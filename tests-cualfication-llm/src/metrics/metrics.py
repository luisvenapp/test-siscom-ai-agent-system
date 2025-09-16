from typing import Dict, Any, List
import re
import statistics
import json


def keyword_coverage(text: str, must_include: List[str], must_not_include: List[str]) -> Dict[str, Any]:
    lower = text.lower()
    inc_hits = sum(1 for k in must_include if k.lower() in lower)
    not_hits = sum(1 for k in must_not_include if k.lower() in lower)
    coverage = inc_hits / max(1, len(must_include)) if must_include else 1.0
    penalty = not_hits / max(1, len(must_not_include)) if must_not_include else 0.0
    score = max(0.0, coverage - penalty)
    return {
        "include_hits": inc_hits,
        "not_include_hits": not_hits,
        "coverage": coverage,
        "penalty": penalty,
        "score": score
    }


def format_checks(text: str, fmt: Dict[str, Any]) -> Dict[str, Any]:
    results: Dict[str, Any] = {"score": 1.0}
    if not fmt:
        return results
    # Max tokens (muy simple: split por espacios)
    if "max_tokens" in fmt:
        tokens = len(text.strip().split())
        results["max_tokens"] = tokens <= fmt["max_tokens"]
        if not results["max_tokens"]:
            results["score"] *= 0.0
    # Lista con guiones
    if fmt.get("list"):
        items = [ln for ln in text.splitlines() if ln.strip().startswith("-")]
        min_items = fmt.get("min_items", 1)
        results["list_items"] = len(items)
        results["list_ok"] = len(items) >= min_items
        if not results["list_ok"]:
            results["score"] *= 0.0
    # JSON estructurado (opcional)
    if fmt.get("json"):
        try:
            obj = json.loads(text)
            results["json_valid"] = True
            required = fmt.get("required_keys", [])
            missing = [k for k in required if k not in obj]
            results["json_required_ok"] = len(missing) == 0
            if not results["json_required_ok"]:
                results["missing_keys"] = missing
                results["score"] *= 0.0
        except Exception:
            results["json_valid"] = False
            results["score"] *= 0.0
    return results


def exact_match_any(text: str, expected: List[str]) -> Dict[str, Any]:
    ok = text.strip() in expected
    return {"ok": ok, "score": 1.0 if ok else 0.0}


def qualitative_scoring(text: str) -> Dict[str, float]:
    # Heurísticas simples para demo. Se puede reemplazar con evaluadores más avanzados.
    s = text.strip()
    length = len(s)
    sentences = max(1, s.count('.') + s.count('!') + s.count('?'))
    avg_sentence = length / sentences
    clarity = 1.0 if avg_sentence < 280 else 0.6
    style = 1.0 if re.match(r"^[A-ZÁÉÍÓÚÜÑ]", s) else 0.8
    return {
        "claridad": clarity,
        "estilo": style
    }


def aggregate_scores(measures: Dict[str, Any], weights: Dict[str, float], elapsed_s: float, sla_seconds: float) -> float:
    # Normaliza latencia a [0..1] (1 si responde antes del SLA, decae linealmente hasta 0 en 2x SLA)
    if sla_seconds <= 0:
        time_component = 1.0
    else:
        if elapsed_s <= sla_seconds:
            time_component = 1.0
        elif elapsed_s >= 2 * sla_seconds:
            time_component = 0.0
        else:
            time_component = 1.0 - (elapsed_s - sla_seconds) / sla_seconds
    exactitud = measures.get("exactitud", 0.0)
    completitud = measures.get("completitud", 0.0)
    relevancia = measures.get("relevancia", 0.0)
    claridad = measures.get("claridad", 0.0)
    formato = measures.get("formato", 0.0)

    score = (
        weights.get("exactitud", 0.3) * exactitud +
        weights.get("completitud", 0.2) * completitud +
        weights.get("relevancia", 0.2) * relevancia +
        weights.get("claridad", 0.2) * claridad +
        weights.get("formato", 0.1) * formato +
        weights.get("penalizacion_tiempo", -0.05) * (1.0 - time_component)
    )
    return max(0.0, min(1.0, score))


def latency_stats(samples: List[float]) -> Dict[str, float]:
    if not samples:
        return {"p50": 0.0, "p95": 0.0, "avg": 0.0}
    sorted_s = sorted(samples)
    def percentile(p):
        k = int(round((p/100) * (len(sorted_s)-1)))
        return sorted_s[k]
    return {
        "p50": percentile(50),
        "p95": percentile(95),
        "avg": sum(sorted_s)/len(sorted_s)
    }
