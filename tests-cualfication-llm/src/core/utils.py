import json
import os
import time
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


def now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def write_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_filename(*parts: str) -> str:
    base = "__".join(parts)
    return "".join(c if c.isalnum() or c in ("-", "_", ".", " ", "__") else "_" for c in base)


def timing_wrapper(func, *args, **kwargs):
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        ok = True
        err = None
    except Exception as e:
        result = None
        ok = False
        err = str(e)
    end = time.perf_counter()
    return {
        "ok": ok,
        "error": err,
        "elapsed_s": end - start,
        "result": result,
    }

_env_pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

def _expand_env_in_str(s: str) -> str:
    def repl(m):
        var = m.group(1)
        return os.environ.get(var, m.group(0))
    return _env_pattern.sub(repl, s)


def expand_env(data: Any) -> Any:
    """Recorre estructuras y expande ${VAR} en strings con valores de entorno."""
    if isinstance(data, dict):
        return {k: expand_env(v) for k, v in data.items()}
    if isinstance(data, list):
        return [expand_env(x) for x in data]
    if isinstance(data, str):
        return _expand_env_in_str(data)
    return data
