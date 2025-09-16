from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    name: str

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config

    @abstractmethod
    def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
        """
        Debe devolver un dict con al menos:
        {
          "ok": bool,
          "response": str (si ok),
          "error": str (si no ok),
          "raw": Any (opcional)
        }
        """
        raise NotImplementedError
