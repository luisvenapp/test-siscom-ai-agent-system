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

    # Sección de selección de modelo
    model_sel = summary.get("model_selection", {})
    if model_sel:
        lines.append("## Mejor Modelo (composite)\n")
        lines.append(f"- Ganador: {model_sel.get('winner', 'N/D')}\n")
        if model_sel.get('explanation'):
            lines.append(f"- Motivo: {model_sel['explanation']}\n")
        lines.append("- Ranking:\n")
        for i, r in enumerate(model_sel.get('ranking', []), start=1):
            lines.append(f"  {i}. {r.get('agent')} — {r.get('score', 0.0):.3f}")
        lines.append("")

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

    # Benchmarks entre agentes (si hay más de uno)
    if len(summary.get("by_agent", {})) > 1:
        lines.append("\n## Benchmark entre modelos (por agente)\n")
        lines.append("- Comparativa rápida de score y latencia promedio\n")
        for agent, data in summary.get("by_agent", {}).items():
            lat = data.get('latency', {})
            score = data.get('score', {})
            extra_cost = data.get('cost', {}) if isinstance(data.get('cost'), dict) else {}
            cost_avg = extra_cost.get('avg')
            cost_str = f", cost_avg={cost_avg:.4f}" if isinstance(cost_avg, (int, float)) else ""
            lines.append(f"  - {agent}: score_avg={score.get('avg',0):.3f}, lat_avg={lat.get('avg',0):.3f}s, ok={data.get('ok_rate',0.0):.2%}, throughput={data.get('throughput_rps',0):.3f} req/s{cost_str}\n")

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
        cost = data.get('cost')
        if isinstance(cost, dict):
            lines.append(f"- Costos: avg={cost.get('avg',0):.4f}, std={cost.get('std',0):.4f}, total={cost.get('total',0):.4f}\n")
        errs = data.get('errors')
        if isinstance(errs, dict) and errs:
            lines.append("- Principales errores:")
            for idx, (msg, cnt) in enumerate(list(errs.items())[:5], start=1):
                lines.append(f"    {idx}. ({cnt}) {msg}")
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
        "cost_avg": overall.get("cost", {}).get("avg", 0.0),
        "cost_std": overall.get("cost", {}).get("std", 0.0),
        "cost_total": overall.get("cost", {}).get("total", 0.0),
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
            "cost_avg": data.get("cost", {}).get("avg", 0.0) if isinstance(data.get("cost"), dict) else 0.0,
            "cost_std": data.get("cost", {}).get("std", 0.0) if isinstance(data.get("cost"), dict) else 0.0,
            "cost_total": data.get("cost", {}).get("total", 0.0) if isinstance(data.get("cost"), dict) else 0.0,
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
