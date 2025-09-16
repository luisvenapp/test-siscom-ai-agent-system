import os
from typing import Dict, Any, List
from .utils import read_json


def load_scenarios(dir_path: str) -> List[Dict[str, Any]]:
    scenarios = []
    for fname in os.listdir(dir_path):
        if fname.endswith('.json'):
            scenarios.append(read_json(os.path.join(dir_path, fname)))
    return scenarios
