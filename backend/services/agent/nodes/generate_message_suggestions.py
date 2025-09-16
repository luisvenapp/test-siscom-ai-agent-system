from typing import Any, Dict, Optional
import json
import re
import asyncio

from langchain import hub
from langchain.agents import create_tool_calling_agent, AgentExecutor

from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.room_info import AgentInfo
from utils.get_current_date import get_current_date
from services.agent.tools.search_google import get_latest_news, search_google
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)


class GenerateMessageSuggestionsNode(NodeAbstractClass):
    """
    Genera sugerencias de mensajes basadas en el contexto.
    Incluye reintentos automáticos hasta obtener una respuesta útil.
    """


    MAX_ATTEMPTS: int = 4
    INITIAL_BACKOFF_SEC: float = 0.6
    MIN_ACCEPTED_LEN: int = 12  

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        agent_info: AgentInfo = state.get("agent_info", {})
        topic: str = state.get("topic", "")

        agent_name = agent_info.name
        personality = agent_info.personality
        dedication = agent_info.dedication
        qualities = agent_info.qualities
        communication_style = agent_info.communication_style
        language_level = agent_info.language_level
        knowledge_scope = agent_info.knowledge_scope
        response_frequency = agent_info.response_frequency
        tone = agent_info.tone
        emoji_usage = agent_info.emoji_usage
        agent_type = agent_info.agent_type
        some_more = agent_info.some_more
        country = agent_info.country

        prompt_template = await compile_prompt(
            "group_message_suggester",
            agent_name=agent_name,
            dedication=dedication,
            qualities=qualities,
            communication_style=communication_style,
            language_level=language_level,
            knowledge_scope=knowledge_scope,
            response_frequency=response_frequency,
            tone=tone,
            emoji_usage=emoji_usage,
            agent_type=agent_type,
            some_more=some_more,
            country=country,
            personality=personality,
            topic=topic,
            current_date=get_current_date(),
        )

  
        agent_executor = self.initialize_tool_agent()

        backoff = self.INITIAL_BACKOFF_SEC
        last_error: Optional[str] = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
   
                if agent_executor:
                    try:
                        tool_raw = await agent_executor.ainvoke({"input": prompt_template})
                        logger.info(f"\n\nRaw response from tool-agent (attempt {attempt}): {tool_raw}\n\n")
                        suggestion = self._parse_output(tool_raw)
                        if self._is_valid(suggestion):
                            logger.info(f"Generated message suggestions: {suggestion}")
                            return {"answer": suggestion, "error": None}
                    except Exception as e:
                        last_error = f"tool-agent: {e}"
                        logger.warning(f"Tool-agent attempt {attempt} failed: {e}")

   
                direct_raw = await self.llm_manager.ainvoke(prompt=prompt_template)
                logger.info(f"\n\nRaw response from direct LLM (attempt {attempt}): {direct_raw}\n\n")
                suggestion = self._parse_output(direct_raw)
                if self._is_valid(suggestion):
                    logger.info(f"Generated message suggestions: {suggestion}")
                    return {"answer": suggestion, "error": None}

                last_error = "Respuesta vacía o no utilizable"
            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt} raised error: {e}")


            if attempt < self.MAX_ATTEMPTS:
                await asyncio.sleep(backoff)
                backoff *= 2  


        logger.info("Generated message suggestions: (sin sugerencias)")
        if last_error:
            logger.warning(f"Last error after retries: {last_error}")


        return {"answer": "", "error": None}

    def initialize_tool_agent(self) -> Optional[AgentExecutor]:
        """
        Inicializa un agente de LangChain con soporte de herramientas.
        """
        tools = [get_latest_news, search_google]
        try:
            prompt = hub.pull("hwchase17/openai-tools-agent")

            agent = create_tool_calling_agent(
                llm=self.llm_manager.llm,
                tools=tools,
                prompt=prompt,
            )

            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=15,
            )
            return agent_executor
        except Exception as err:
            logger.error(f"Failed to initialize tool agent: {err}")
            return None

 
    def _parse_output(self, raw: Any) -> str:
        """
        Convierte la salida (dict/str/list) a una única cadena “limpia”
        apta para mostrar al usuario (sin 'Final Answer:', sin ```json, etc.)
        """
        text = ""

 
        if isinstance(raw, dict):
 
            for key in ("output", "final_answer", "final", "text", "answer", "content"):
                if key in raw and isinstance(raw[key], str) and raw[key].strip():
                    text = raw[key]
                    break
            if not text:
                text = json.dumps(raw, ensure_ascii=False)
        elif isinstance(raw, list):
            text = " ".join([str(x) for x in raw if str(x).strip()])
        else:
            text = str(raw or "")

 
        text = re.sub(r"^```(?:json|md|markdown)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)

 
        cleaned = text.strip()
        try:
            if cleaned.startswith("{") or cleaned.startswith("["):
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
 
                    for item in parsed:
                        if isinstance(item, str) and item.strip():
                            cleaned = item.strip()
                            break
                elif isinstance(parsed, dict):
 
                    for key in ("output", "text", "final_answer"):
                        if key in parsed and isinstance(parsed[key], str) and parsed[key].strip():
                            cleaned = parsed[key].strip()
                            break
        except Exception:
 
            pass

 
        cleaned = re.sub(r"^\s*(final\s*answer|respuesta\s*final)\s*:\s*", "", cleaned, flags=re.IGNORECASE)

 
        cleaned = cleaned.strip().strip('"').strip("'").strip()

        return cleaned

    def _is_valid(self, text: Optional[str]) -> bool:
        """
        Criterio simple de validez: no vacío y con longitud mínima.
        """
        if not text:
            return False
        if text.lower() in {"(sin sugerencias)", "sin sugerencias"}:
            return False
        return len(text) >= self.MIN_ACCEPTED_LEN
