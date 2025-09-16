import os
from typing import Dict, Any, Optional
from .utils import ensure_dir, safe_filename

class TestLogger:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        ensure_dir(base_dir)

    def log_path(self, agent_name: str, timestamp: str, iteration: int, scenario: Optional[str] = None, case_id: Optional[str] = None) -> str:
        # Requisitos mínimos: agente, timestamp, iteración.
        # Para evitar colisiones añadimos escenario y caso cuando están disponibles.
        parts = [f"{agent_name}", f"{timestamp}", f"iter-{iteration}"]
        if scenario:
            parts.append(f"{scenario}")
        if case_id:
            parts.append(f"{case_id}")
        fname = safe_filename(*parts) + ".log"
        return os.path.join(self.base_dir, fname)

    def write_log(self, agent_name: str, timestamp: str, iteration: int, content: str, scenario: Optional[str] = None, case_id: Optional[str] = None) -> str:
        path = self.log_path(agent_name, timestamp, iteration, scenario, case_id)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path
