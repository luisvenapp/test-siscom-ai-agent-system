import os
import time
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import now_ts, ensure_dir, write_json
from .logger import TestLogger
from .scenario_loader import load_scenarios
from ..agents.base import BaseAgent
from ..agents.ollama_agent import OllamaAgent
from ..agents.http_agent import HttpAgent
from ..agents.cli_agent import CliAgent
from ..agents.openai_agent import OpenAIAgent
from ..agents.deepseek_agent import DeepseekAgent
from ..agents.gemini_agent import GeminiAgent
from ..metrics.metrics import keyword_coverage, format_checks, exact_match_any, qualitative_scoring, aggregate_scores


AGENT_TYPES = {
    "ollama": OllamaAgent,
    "http": HttpAgent,
    "cli": CliAgent,
    "openai": OpenAIAgent,
    "deepseek": DeepseekAgent,
    "gemini": GeminiAgent,
}


class Orchestrator:
    def __init__(self, config: Dict[str, Any], base_dir: str):
        self.config = config
        self.base_dir = base_dir
        self.log_dir = os.path.join(base_dir, config.get("log_dir", "logs"))
        self.reports_dir = os.path.join(base_dir, config.get("reports_dir", "reports"))
        self.scenarios_dir = os.path.join(base_dir, config.get("scenarios_dir", "scenarios"))
        self.thresholds = config.get("rubrics", {}).get("thresholds", {"aprobado": 0.7, "excelente": 0.9})
        ensure_dir(self.log_dir)
        ensure_dir(self.reports_dir)
        self.logger = TestLogger(self.log_dir)
        self.timestamp = now_ts()

    def build_agents(self) -> List[BaseAgent]:
        agents = []
        for a in self.config.get("agents", []):
            name = a.get("name")
            typ = a.get("type")
            cls = AGENT_TYPES.get(typ)
            if not cls:
                continue
            agents.append(cls(name=name, config=a))
        return agents

    def _run_single(self, agent: BaseAgent, scenario: Dict[str, Any], case: Dict[str, Any], i: int, timeout: float, weights: Dict[str, float]) -> Dict[str, Any]:
        prompt = case.get("prompt", "")
        expected = case.get("expected", {})
        # Prioriza reintentos por agente si se especifica; si no, usa el global
        retries = int(getattr(agent, 'config', {}).get('retries', self.config.get("max_model_fail_retries", 0)))
        try:
            retries = int(retries)
        except Exception:
            retries = 0
        attempt = 0
        last_exc = None
        t0 = time.perf_counter()
        while attempt <= retries:
            try:
                start = time.perf_counter()
                result = agent.infer(prompt, timeout)
                elapsed = time.perf_counter() - start
                # Si la respuesta no es ok y aún quedan reintentos, reintentar
                if not result.get("ok", False) and attempt < retries:
                    attempt += 1
                    continue
                break
            except Exception as e:
                last_exc = e
                attempt += 1
                if attempt > retries:
                    result = {"ok": False, "error": str(last_exc)}
                    elapsed = time.perf_counter() - t0
                    break
        else:
            # safety fallback
            result = {"ok": False, "error": "unknown error"}
            elapsed = timeout

        ok = result.get("ok", False)
        response = result.get("response") if ok else ""
        error = result.get("error") if not ok else None

        # Métricas por caso
        kw = keyword_coverage(response, expected.get("must_include", []), expected.get("must_not_include", [])) if ok else {"score": 0}
        fmt = format_checks(response, expected.get("format", {})) if ok else {"score": 0}
        exm = exact_match_any(response, expected.get("exact_match_any", [])) if ok else {"score": 0}
        qual = qualitative_scoring(response) if ok else {"claridad": 0.0, "estilo": 0.0}

        measures = {
            "exactitud": max(exm.get("score", 0.0), kw.get("score", 0.0)),
            "completitud": kw.get("coverage", 0.0),
            "relevancia": 1.0 if kw.get("not_include_hits", 0) == 0 else 0.5,
            "claridad": qual.get("claridad", 0.0),
            "formato": fmt.get("score", 0.0),
        }
        final_score = aggregate_scores(measures, weights, elapsed, timeout)
        thr_ap = self.thresholds.get("aprobado", 0.7)
        thr_ex = self.thresholds.get("excelente", 0.9)
        if final_score >= thr_ex:
            grade = "excelente"
        elif final_score >= thr_ap:
            grade = "aprobado"
        else:
            grade = "insuficiente"

        response_tokens = len(response.strip().split()) if ok else 0
        response_chars = len(response) if ok else 0
        record = {
            "timestamp": self.timestamp,
            "agent": agent.name,
            "scenario": scenario.get("name"),
            "case_id": case.get("id"),
            "iteration": i,
            "elapsed_s": elapsed,
            "ok": ok,
            "error": error,
            "response": response,
            "response_tokens": response_tokens,
            "response_chars": response_chars,
            "measures": measures,
            "kw": kw,
            "fmt": fmt,
            "exact_match": exm,
            "qual": qual,
            "final_score": final_score,
            "grade": grade,
        }

        # Log detallado por iteración
        log_content = {
            "timestamp": self.timestamp,
            "agent": agent.name,
            "scenario": scenario.get("name"),
            "case_id": case.get("id"),
            "iteration": i,
            "prompt": prompt,
            "result": record,
        }
        log_text = json_dumps(log_content)
        self.logger.write_log(agent.name, self.timestamp, i, log_text, scenario.get("name"), case.get("id"))
        return record

    def run(self) -> Dict[str, Any]:
        iterations = int(self.config.get("iterations", 10))
        timeout = float(self.config.get("timeout_seconds", 120))
        weights = self.config.get("rubrics", {}).get("weights", {})
        concurrency = int(self.config.get("concurrency", 1))
        agent_execution = self.config.get("agent_execution", "sequential").lower()
        within_agent_concurrency = int(self.config.get("within_agent_concurrency", concurrency))

        scenarios = load_scenarios(self.scenarios_dir)
        agents = self.build_agents()

        total_cases = sum(len(s.get("cases", [])) for s in scenarios)
        total_tasks = max(0, len(agents) * total_cases * max(1, iterations))
        progress_step = max(1, total_tasks // 20)  # ~5% steps
        completed = 0

        print(f"[{self.timestamp}] Starting tests: agents={len(agents)}, scenarios={len(scenarios)}, cases={total_cases}, iterations={iterations}, total={total_tasks}, mode={agent_execution}, concurrency={concurrency}, within_agent_concurrency={within_agent_concurrency}", flush=True)

        all_records: List[Dict[str, Any]] = []

        if agent_execution == "parallel" and concurrency > 1:
            # Ejecuta todas las combinaciones en paralelo (posible mezcla entre agentes)
            with ThreadPoolExecutor(max_workers=concurrency) as ex:
                futures = []
                for agent in agents:
                    for scenario in scenarios:
                        for case in scenario.get("cases", []):
                            for i in range(1, iterations + 1):
                                futures.append(ex.submit(self._run_single, agent, scenario, case, i, timeout, weights))
                for fut in as_completed(futures):
                    try:
                        rec = fut.result()
                        all_records.append(rec)
                    except Exception as e:
                        all_records.append({"ok": False, "error": str(e)})
                    finally:
                        completed += 1
                        if completed % progress_step == 0 or completed == total_tasks:
                            print(f"Progress: {completed}/{total_tasks} ({(completed/max(1,total_tasks))*100:.1f}%)", flush=True)
        else:
            # Secuencial por agente; si concurrency>1, paraleliza solo dentro del agente actual
            for agent in agents:
                if within_agent_concurrency > 1:
                    with ThreadPoolExecutor(max_workers=within_agent_concurrency) as ex:
                        futures = []
                        for scenario in scenarios:
                            for case in scenario.get("cases", []):
                                for i in range(1, iterations + 1):
                                    futures.append(ex.submit(self._run_single, agent, scenario, case, i, timeout, weights))
                        for fut in as_completed(futures):
                            try:
                                rec = fut.result()
                                all_records.append(rec)
                            except Exception as e:
                                all_records.append({"ok": False, "error": str(e)})
                            finally:
                                completed += 1
                                if completed % progress_step == 0 or completed == total_tasks:
                                    print(f"Progress: {completed}/{total_tasks} ({(completed/max(1,total_tasks))*100:.1f}%)", flush=True)
                    print(f"Agent completed: {agent.name}", flush=True)
                else:
                    for scenario in scenarios:
                        for case in scenario.get("cases", []):
                            for i in range(1, iterations + 1):
                                rec = self._run_single(agent, scenario, case, i, timeout, weights)
                                all_records.append(rec)
                                completed += 1
                                if completed % progress_step == 0 or completed == total_tasks:
                                    print(f"Progress: {completed}/{total_tasks} ({(completed/max(1,total_tasks))*100:.1f}%)", flush=True)
                    print(f"Agent completed: {agent.name}", flush=True)

        # Persistimos resultados crudos
        raw_path = os.path.join(self.reports_dir, f"raw_results__{self.timestamp}.json")
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(json_dumps(all_records))
        print(f"Wrote raw results to: {raw_path}", flush=True)

        return {"timestamp": self.timestamp, "records": all_records}


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)
