from typing import Any, Dict, List, Optional
import json
import re

from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class AgentReplySplitterNode(NodeAbstractClass):
    """
    Convierte la respuesta cruda del agente (state['answer']) en una lista de
    mensajes sin fences de código ni prefijos como 'json' o 'Final Answer:'.
    Devuelve en el estado: {"list_message": List[str]}.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        answer: str = (state.get("answer") or "").strip()

        if not answer:
            logger.warning("Respuesta vacía en AgentReplySplitterNode.")
            return {"list_message": []}

        
        cleaned = self._strip_code_fences(answer)
        cleaned = self._strip_labels(cleaned).strip()

        messages = self._parse_array(cleaned)

        if messages is None:
            array_like = self._extract_first_json_array(cleaned)
            messages = self._parse_array(array_like) if array_like else None

        # 4) Si aún no es array, lo tratamos como un único mensaje
        if messages is None:
            messages = [cleaned] if cleaned else []

        # 5) Normalización final
        messages = [str(m).strip() for m in messages if str(m).strip()][0]
        
        prompt_template = await compile_prompt(
            "agent_replay_splitter",
            agent_response=messages,
        )
        
        list_message = await self.llm_manager.ainvoke(
                prompt=prompt_template
            )
        
        cleaned = self._strip_code_fences(list_message)
        cleaned = self._strip_labels(cleaned).strip()
        array_like = self._extract_first_json_array(cleaned)
        messages = self._parse_array(array_like) if array_like else None
        return {"list_message": messages}

    # ---------- Helpers ----------

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """
        Elimina cualquier fence tipo:
          ```json\n...\n```
        o ```lang y los ``` de cierre, en cualquier parte del texto.
        """
        if not text:
            return ""
        t = text

        t = re.sub(r"```[a-zA-Z0-9_-]*\s*\n", "", t)
        t = t.replace("```", "")

        t = re.sub(r"^\s*json\s*", "", t, flags=re.IGNORECASE)

        return t.strip()

    @staticmethod
    def _strip_labels(text: str) -> str:
        """
        Quita prefijos comunes como 'Final Answer:', 'Respuesta:', 'Output:', etc.
        """
        if not text:
            return ""
        patterns = [
            r"^\s*final\s*answer\s*:\s*",     
            r"^\s*respuesta\s*:\s*",          
            r"^\s*output\s*:\s*",             
            r"^\s*answer\s*:\s*",             
        ]
        t = text
        for p in patterns:
            t = re.sub(p, "", t, flags=re.IGNORECASE)
        return t

    @staticmethod
    def _parse_array(text: Optional[str]) -> Optional[List[str]]:
        if text is None:
            return None
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x) for x in data]
            return None
        except Exception:
            return None

    @staticmethod
    def _extract_first_json_array(text: str) -> Optional[str]:
        """
        Extrae el primer bloque con forma de array JSON (lo más general posible).
        """
        if not text:
            return None
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1].strip()
        m = re.search(r"\[\s*(?:\".*?\"(?:\s*,\s*\".*?\")*)\s*\]", text, flags=re.DOTALL)
        return m.group(0).strip() if m else None
