from typing import Dict, Any, List, Tuple

RECOGNIZED_AGENT_TYPES = {"ollama", "http", "cli"}


def validate_config(config: Dict[str, Any]) -> List[str]:
    msgs: List[str] = []
    if not isinstance(config, dict):
        return ["config.json no es un objeto JSON"]

    it = config.get("iterations")
    if not isinstance(it, int) or it < 1:
        msgs.append("iterations debe ser un entero >= 1")

    agents = config.get("agents", [])
    if not agents or not isinstance(agents, list):
        msgs.append("agents debe ser una lista no vacía")
    else:
        for idx, a in enumerate(agents):
            name = a.get("name")
            typ = a.get("type")
            if not name:
                msgs.append(f"agent[{idx}] sin name")
            if typ not in RECOGNIZED_AGENT_TYPES:
                msgs.append(f"agent[{idx}] type desconocido: {typ}")
            if typ == "http":
                if not a.get("base_url"):
                    msgs.append(f"agent[{idx}] http sin base_url")
            if typ == "ollama":
                if not a.get("base_url"):
                    msgs.append(f"agent[{idx}] ollama sin base_url")
                if not a.get("model"):
                    msgs.append(f"agent[{idx}] ollama sin model")
            if typ == "cli":
                if not a.get("cmd"):
                    msgs.append(f"agent[{idx}] cli sin cmd")

    rubrics = config.get("rubrics", {})
    weights = rubrics.get("weights", {})
    if not isinstance(weights, dict) or not weights:
        msgs.append("rubrics.weights debe ser un objeto no vacío")

    return msgs


def validate_scenarios(scenarios: List[Dict[str, Any]]) -> List[str]:
    msgs: List[str] = []
    for sidx, s in enumerate(scenarios):
        name = s.get("name") or f"scenario_{sidx}"
        cases = s.get("cases")
        if not isinstance(cases, list) or not cases:
            msgs.append(f"Escenario '{name}' sin casos")
            continue
        for cidx, c in enumerate(cases):
            cid = c.get("id")
            prompt = c.get("prompt")
            if not cid:
                msgs.append(f"Escenario '{name}' caso[{cidx}] sin id")
            if not prompt:
                msgs.append(f"Escenario '{name}' caso[{cid or cidx}] sin prompt")
            expected = c.get("expected", {})
            if not isinstance(expected, dict):
                msgs.append(f"Escenario '{name}' caso[{cid or cidx}] expected debe ser objeto")
                continue
            fmt = expected.get("format", {})
            if fmt and not isinstance(fmt, dict):
                msgs.append(f"Escenario '{name}' caso[{cid or cidx}] format debe ser objeto")
            if fmt.get("json") and fmt.get("required_keys") and not isinstance(fmt.get("required_keys"), list):
                msgs.append(f"Escenario '{name}' caso[{cid or cidx}] required_keys debe ser lista")
    return msgs
