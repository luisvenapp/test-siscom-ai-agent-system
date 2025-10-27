from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics
from ..metrics.metrics import latency_stats


def _grade_counts(group: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {"excelente": 0, "aprobado": 0, "insuficiente": 0}
    for g in group:
        grd = g.get("grade")
        if grd in counts:
            counts[grd] += 1
    return counts


def _error_breakdown(group: List[Dict[str, Any]]) -> Dict[str, int]:
    errs: Dict[str, int] = defaultdict(int)
    for g in group:
        e = (g.get("error") or "").strip()
        if not e:
            continue
        # Simple normalización: recorta errores largos a 120 chars para agrupar
        key = e[:120]
        errs[key] += 1
    return dict(sorted(errs.items(), key=lambda kv: kv[1], reverse=True))


def _cost_stats_for_group(group: List[Dict[str, Any]], cost_per_1k_output_tokens: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
    if not cost_per_1k_output_tokens:
        return None
    costs: List[float] = []
    for g in group:
        agent = g.get("agent")
        cpk = cost_per_1k_output_tokens.get(agent)
        if cpk is None:
            # Si no hay precio definido para este agente, ignora este record
            continue
        toks = float(g.get("response_tokens", 0) or 0)
        costs.append((toks / 1000.0) * float(cpk))
    if not costs:
        return None
    return {
        "avg": sum(costs) / len(costs),
        "std": statistics.pstdev(costs) if len(costs) > 1 else 0.0,
        "total": sum(costs),
    }


def _summarise(group: List[Dict[str, Any]], *, cost_per_1k_output_tokens: Optional[Dict[str, float]] = None, include_error_breakdown: bool = False) -> Dict[str, Any]:
    lats = [float(g.get('elapsed_s', 0.0) or 0.0) for g in group]
    oks = sum(1 for g in group if g.get('ok'))
    scores = [float(g.get('final_score', 0.0) or 0.0) for g in group]
    tokens = [int(g.get('response_tokens', 0) or 0) for g in group]
    chars = [int(g.get('response_chars', 0) or 0) for g in group]
    grades = _grade_counts(group)
    total_time = sum(lats)
    throughput = (len(group) / total_time) if total_time > 0 else 0.0

    summary: Dict[str, Any] = {
        "count": len(group),
        "ok_rate": oks / max(1, len(group)),
        "latency": {**latency_stats(lats), "std": statistics.pstdev(lats) if len(lats) > 1 else 0.0},
        "throughput_rps": throughput,
        "score": {
            "avg": sum(scores) / max(1, len(scores)),
            "std": statistics.pstdev(scores) if len(scores) > 1 else 0.0
        },
        "response": {
            "tokens_avg": sum(tokens) / max(1, len(tokens)),
            "chars_avg": sum(chars) / max(1, len(chars))
        },
        "grades": grades
    }

    cstats = _cost_stats_for_group(group, cost_per_1k_output_tokens)
    if cstats:
        summary["cost"] = cstats

    if include_error_breakdown:
        summary["errors"] = _error_breakdown(group)

    return summary


def aggregate_runs(run_records: List[Dict[str, Any]], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Aggregates raw run records into summaries at several levels.
    options:
      - cost_per_1k_output_tokens: Dict[agent_name, float]
      - include_error_breakdown: bool
    """
    options = options or {}
    cost_map: Optional[Dict[str, float]] = options.get("cost_per_1k_output_tokens")
    include_errs: bool = bool(options.get("include_error_breakdown", False))

    # run_records: [{agent, scenario, case_id, iteration, elapsed_s, final_score, grade, ok, ...}]
    by_agent = defaultdict(list)
    by_scenario = defaultdict(list)
    by_agent_case = defaultdict(list)  # key: (agent, scenario, case_id)

    for r in run_records:
        a = r.get('agent', '__unknown__')
        s = r.get('scenario', '__unknown__')
        c = r.get('case_id', '__unknown__')
        by_agent[a].append(r)
        by_scenario[s].append(r)
        by_agent_case[(a, s, c)].append(r)

    summary = {
        "by_agent": {k: _summarise(v, cost_per_1k_output_tokens=cost_map, include_error_breakdown=include_errs) for k, v in by_agent.items()},
        "by_scenario": {k: _summarise(v, cost_per_1k_output_tokens=cost_map, include_error_breakdown=include_errs) for k, v in by_scenario.items()},
        "by_agent_case": {
            f"{a}::{s}::{c}": _summarise(v, cost_per_1k_output_tokens=cost_map, include_error_breakdown=include_errs) for (a, s, c), v in by_agent_case.items()
        },
        "overall": _summarise(run_records, cost_per_1k_output_tokens=cost_map, include_error_breakdown=include_errs)
    }
    return summary


def _min_max_norm(values: List[float], invert: bool = False) -> List[float]:
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax - vmin == 0:
        norm = [1.0 for _ in values]
    else:
        norm = [(v - vmin) / (vmax - vmin) for v in values]
    if invert:
        norm = [1.0 - x for x in norm]
    return [max(0.0, min(1.0, float(x))) for x in norm]


def build_model_selection(summary: Dict[str, Any], decision_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Computes a composite ranking across agents based on multiple metrics.
    decision_cfg example:
      {
        "weights": {
          "score_avg": 0.4,
          "ok_rate": 0.2,
          "latency_avg": 0.15,
          "latency_p95": 0.10,
          "throughput_rps": 0.10,
          "score_std": 0.03,
          "latency_std": 0.02,
          "tokens_avg": 0.0
        }
      }
    """
    decision_cfg = decision_cfg or {}
    weights: Dict[str, float] = {
        "score_avg": 0.4,
        "ok_rate": 0.2,
        "latency_avg": 0.15,
        "latency_p95": 0.10,
        "throughput_rps": 0.08,
        "score_std": 0.03,
        "latency_std": 0.02,
        "tokens_avg": 0.0,
        "cost_avg": 0.02,  # small penalty by default; increase if cost matters
    }
    weights.update(decision_cfg.get("weights", {}))

    by_agent: Dict[str, Any] = summary.get("by_agent", {})
    agents = list(by_agent.keys())
    if not agents:
        return {"weights": weights, "per_agent": {}, "ranking": [], "winner": None}

    # Collect raw metrics
    raw = {
        "score_avg": [float(by_agent[a].get("score", {}).get("avg", 0.0) or 0.0) for a in agents],
        "ok_rate": [float(by_agent[a].get("ok_rate", 0.0) or 0.0) for a in agents],
        "latency_avg": [float(by_agent[a].get("latency", {}).get("avg", 0.0) or 0.0) for a in agents],
        "latency_p95": [float(by_agent[a].get("latency", {}).get("p95", 0.0) or 0.0) for a in agents],
        "throughput_rps": [float(by_agent[a].get("throughput_rps", 0.0) or 0.0) for a in agents],
        "score_std": [float(by_agent[a].get("score", {}).get("std", 0.0) or 0.0) for a in agents],
        "latency_std": [float(by_agent[a].get("latency", {}).get("std", 0.0) or 0.0) for a in agents],
        "tokens_avg": [float(by_agent[a].get("response", {}).get("tokens_avg", 0.0) or 0.0) for a in agents],
        "cost_avg": [float((by_agent[a].get("cost", {}) or {}).get("avg", 0.0) or 0.0) for a in agents],
    }

    # Normalize; invert for metrics where lower is better
    norm = {
        "score_avg": _min_max_norm(raw["score_avg"]),
        "ok_rate": _min_max_norm(raw["ok_rate"]),
        "latency_avg": _min_max_norm(raw["latency_avg"], invert=True),
        "latency_p95": _min_max_norm(raw["latency_p95"], invert=True),
        "throughput_rps": _min_max_norm(raw["throughput_rps"]),
        "score_std": _min_max_norm(raw["score_std"], invert=True),
        "latency_std": _min_max_norm(raw["latency_std"], invert=True),
        "tokens_avg": _min_max_norm(raw["tokens_avg"], invert=True),  # Prefer conciseness by default
        "cost_avg": _min_max_norm(raw["cost_avg"], invert=True),  # Lower cost is better
    }

    per_agent: Dict[str, Any] = {}
    for idx, a in enumerate(agents):
        comp = 0.0
        contribs: Dict[str, float] = {}
        for m, w in weights.items():
            v = norm.get(m, [0.0] * len(agents))[idx]
            comp += w * v
            contribs[m] = w * v
        per_agent[a] = {
            "composite": comp,
            "norm": {m: norm[m][idx] for m in norm},
            "raw": {m: raw[m][idx] for m in raw},
            "contribs": contribs,
        }

    ranking = sorted(({"agent": a, "score": per_agent[a]["composite"]} for a in agents), key=lambda x: x["score"], reverse=True)
    winner = ranking[0]["agent"] if ranking else None

    # Build short explanation focusing on top 2 contributing metrics for the winner
    explanation = None
    if winner:
        contribs = per_agent[winner]["contribs"]
        top_metrics = sorted(contribs.items(), key=lambda kv: kv[1], reverse=True)[:2]
        parts = [f"'{m}'" for m, _ in top_metrics]
        explanation = f"Modelo ganador: {winner} por su balance en {', '.join(parts)} y desempeño general."

    return {
        "weights": weights,
        "agents": agents,
        "per_agent": per_agent,
        "ranking": ranking,
        "winner": winner,
        "explanation": explanation,
    }
