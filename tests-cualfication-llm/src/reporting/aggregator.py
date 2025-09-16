from typing import List, Dict, Any
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


def _summarise(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    lats = [g.get('elapsed_s', 0.0) for g in group]
    oks = sum(1 for g in group if g.get('ok'))
    scores = [g.get('final_score', 0.0) for g in group]
    tokens = [g.get('response_tokens', 0) for g in group]
    chars = [g.get('response_chars', 0) for g in group]
    grades = _grade_counts(group)
    total_time = sum(lats)
    throughput = (len(group) / total_time) if total_time > 0 else 0.0
    return {
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


def aggregate_runs(run_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    # run_records: [{agent, scenario, case_id, iteration, elapsed_s, final_score, grade, ok, ...}]
    by_agent = defaultdict(list)
    by_scenario = defaultdict(list)
    by_agent_case = defaultdict(list)  # key: (agent, scenario, case_id)

    for r in run_records:
        by_agent[r['agent']].append(r)
        by_scenario[r['scenario']].append(r)
        by_agent_case[(r['agent'], r['scenario'], r['case_id'])].append(r)

    summary = {
        "by_agent": {k: _summarise(v) for k, v in by_agent.items()},
        "by_scenario": {k: _summarise(v) for k, v in by_scenario.items()},
        "by_agent_case": {
            f"{a}::{s}::{c}": _summarise(v) for (a, s, c), v in by_agent_case.items()
        },
        "overall": _summarise(run_records)
    }
    return summary
