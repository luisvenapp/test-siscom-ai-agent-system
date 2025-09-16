import os
from typing import Dict, Any
from ..core.utils import write_json
import csv


def export_json(path: str, data: Dict[str, Any]) -> None:
    write_json(path, data)


def _fmt_latency(lat: Dict[str, Any]) -> str:
    return f"p50 {lat.get('p50',0):.3f}s | p95 {lat.get('p95',0):.3f}s | avg {lat.get('avg',0):.3f}s | std {lat.get('std',0):.3f}s"


def export_markdown(path: str, summary: Dict[str, Any]) -> None:
    lines = []
    lines.append("# Resumen de pruebas LLM\n")
    lines.append("## Global\n")
    overall = summary.get("overall", {})
    lines.append(f"- Tests: {overall.get('count', 0)}\n")
    lines.append(f"- Éxito: {overall.get('ok_rate', 0.0):.2%}\n")
    lat = overall.get('latency', {})
    lines.append(f"- Latencia: {_fmt_latency(lat)}\n")
    lines.append(f"- Throughput: {overall.get('throughput_rps',0):.3f} req/s\n")
    score = overall.get('score', {})
    if score:
        lines.append(f"- Score: avg {score.get('avg',0):.3f} | std {score.get('std',0):.3f}\n")

    lines.append("\n## Por agente\n")
    for agent, data in summary.get("by_agent", {}).items():
        lines.append(f"### {agent}\n")
        lines.append(f"- Tests: {data.get('count',0)}\n")
        lines.append(f"- Éxito: {data.get('ok_rate',0.0):.2%}\n")
        lat = data.get('latency', {})
        lines.append(f"- Latencia: {_fmt_latency(lat)}\n")
        lines.append(f"- Throughput: {data.get('throughput_rps',0):.3f} req/s\n")
        score = data.get('score', {})
        lines.append(f"- Score: avg {score.get('avg',0):.3f} | std {score.get('std',0):.3f}\n")
        grades = data.get('grades', {})
        if grades:
            lines.append(f"- Calificaciones: excelente={grades.get('excelente',0)}, aprobado={grades.get('aprobado',0)}, insuficiente={grades.get('insuficiente',0)}\n")
        lines.append("\n")

    lines.append("\n## Por escenario\n")
    for scene, data in summary.get("by_scenario", {}).items():
        lines.append(f"### {scene}\n")
        lines.append(f"- Tests: {data.get('count',0)}\n")
        lines.append(f"- Éxito: {data.get('ok_rate',0.0):.2%}\n")
        lat = data.get('latency', {})
        lines.append(f"- Latencia: {_fmt_latency(lat)}\n")
        score = data.get('score', {})
        lines.append(f"- Score: avg {score.get('avg',0):.3f} | std {score.get('std',0):.3f}\n\n")

    # Opcional por agente/escenario/caso
    lines.append("\n## Por agente/escenario/caso (resumen)\n")
    for key, data in summary.get("by_agent_case", {}).items():
        lines.append(f"- {key}: count={data.get('count',0)}, ok={data.get('ok_rate',0.0):.2%}, score_avg={data.get('score',{}).get('avg',0):.3f}\n")

    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def export_csv(path: str, summary: Dict[str, Any]) -> None:
    rows = []
    # Overall row
    overall = summary.get("overall", {})
    rows.append({
        "category": "overall",
        "key": "all",
        "count": overall.get("count", 0),
        "ok_rate": overall.get("ok_rate", 0.0),
        "lat_p50": overall.get("latency", {}).get("p50", 0.0),
        "lat_p95": overall.get("latency", {}).get("p95", 0.0),
        "lat_avg": overall.get("latency", {}).get("avg", 0.0),
        "lat_std": overall.get("latency", {}).get("std", 0.0),
        "throughput_rps": overall.get("throughput_rps", 0.0),
        "score_avg": overall.get("score", {}).get("avg", 0.0),
        "score_std": overall.get("score", {}).get("std", 0.0),
        "tokens_avg": overall.get("response", {}).get("tokens_avg", 0.0),
        "chars_avg": overall.get("response", {}).get("chars_avg", 0.0),
        "grade_excelente": overall.get("grades", {}).get("excelente", 0),
        "grade_aprobado": overall.get("grades", {}).get("aprobado", 0),
        "grade_insuficiente": overall.get("grades", {}).get("insuficiente", 0),
    })
    # By agent
    for agent, data in summary.get("by_agent", {}).items():
        rows.append({
            "category": "agent",
            "key": agent,
            "count": data.get("count", 0),
            "ok_rate": data.get("ok_rate", 0.0),
            "lat_p50": data.get("latency", {}).get("p50", 0.0),
            "lat_p95": data.get("latency", {}).get("p95", 0.0),
            "lat_avg": data.get("latency", {}).get("avg", 0.0),
            "lat_std": data.get("latency", {}).get("std", 0.0),
            "throughput_rps": data.get("throughput_rps", 0.0),
            "score_avg": data.get("score", {}).get("avg", 0.0),
            "score_std": data.get("score", {}).get("std", 0.0),
            "tokens_avg": data.get("response", {}).get("tokens_avg", 0.0),
            "chars_avg": data.get("response", {}).get("chars_avg", 0.0),
            "grade_excelente": data.get("grades", {}).get("excelente", 0),
            "grade_aprobado": data.get("grades", {}).get("aprobado", 0),
            "grade_insuficiente": data.get("grades", {}).get("insuficiente", 0),
        })
    # By scenario
    for scene, data in summary.get("by_scenario", {}).items():
        rows.append({
            "category": "scenario",
            "key": scene,
            "count": data.get("count", 0),
            "ok_rate": data.get("ok_rate", 0.0),
            "lat_p50": data.get("latency", {}).get("p50", 0.0),
            "lat_p95": data.get("latency", {}).get("p95", 0.0),
            "lat_avg": data.get("latency", {}).get("avg", 0.0),
            "lat_std": data.get("latency", {}).get("std", 0.0),
            "score_avg": data.get("score", {}).get("avg", 0.0),
            "score_std": data.get("score", {}).get("std", 0.0),
            "tokens_avg": data.get("response", {}).get("tokens_avg", 0.0),
            "chars_avg": data.get("response", {}).get("chars_avg", 0.0),
            "grade_excelente": data.get("grades", {}).get("excelente", 0),
            "grade_aprobado": data.get("grades", {}).get("aprobado", 0),
            "grade_insuficiente": data.get("grades", {}).get("insuficiente", 0),
        })
    # By agent-case
    for key, data in summary.get("by_agent_case", {}).items():
        rows.append({
            "category": "agent_case",
            "key": key,
            "count": data.get("count", 0),
            "ok_rate": data.get("ok_rate", 0.0),
            "lat_p50": data.get("latency", {}).get("p50", 0.0),
            "lat_p95": data.get("latency", {}).get("p95", 0.0),
            "lat_avg": data.get("latency", {}).get("avg", 0.0),
            "lat_std": data.get("latency", {}).get("std", 0.0),
            "score_avg": data.get("score", {}).get("avg", 0.0),
            "score_std": data.get("score", {}).get("std", 0.0),
            "tokens_avg": data.get("response", {}).get("tokens_avg", 0.0),
            "chars_avg": data.get("response", {}).get("chars_avg", 0.0),
            "grade_excelente": data.get("grades", {}).get("excelente", 0),
            "grade_aprobado": data.get("grades", {}).get("aprobado", 0),
            "grade_insuficiente": data.get("grades", {}).get("insuficiente", 0),
        })

    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
