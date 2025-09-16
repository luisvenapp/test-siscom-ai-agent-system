import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent

from core.logging_config import get_logger
from schemas.message import Message
from services.agent.nodes.base import NodeAbstractClass
from services.agent.tools.search_google import get_latest_news, search_google
from utils.get_current_date import get_current_date, get_current_hour
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)


class PersonalizeNode(NodeAbstractClass):
    """
    Node to summarize past conversation messages into key bullet points.

    Expects 'messages' in state as a list of Message objects and outputs
    'conversation_summary' and 'question'.
    """

    MAX_ATTEMPTS: int = 4
    INITIAL_BACKOFF_SEC: float = 0.6
    MIN_ACCEPTED_LEN: int = 12

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize the conversation and extract the user's last question.

        Args:
            state: Dictionary with key 'messages' containing a list of Message objects.

        Returns:
            Updated state with 'conversation_summary' and 'question'.
        """
        messages: List[Message] = state.get("conversation_summary", [])
        recent_message: str = state.get("question", "")
        group_context = state.get("room_details", "")
        personalize_agent = state.get("personalize_agent", "")
        slang_context = state.get("slang_context", "")
        personality = personalize_agent.get("personality", "").lower().strip()

        agent_to_execute = [
            agent
            for agent in group_context.agents
            if agent.id == personalize_agent.get("id", "")
        ][0]
        agent_name = agent_to_execute.name
        dedication = agent_to_execute.dedication
        qualities = agent_to_execute.qualities
        communication_style = agent_to_execute.communication_style
        language_level = agent_to_execute.language_level
        knowledge_scope = agent_to_execute.knowledge_scope
        response_frequency = agent_to_execute.response_frequency
        tone = agent_to_execute.tone
        emoji_usage = agent_to_execute.emoji_usage
        agent_type = agent_to_execute.agent_type
        some_more = agent_to_execute.some_more
        country = agent_to_execute.country

        slang_context = [
            analysis for analysis in slang_context if analysis.country == country
        ]

        if not slang_context:
            logger.warning(f"No slang analysis found for country {country}.")
            slang_context = [
                {
                    "representative_phrases": [],
                    "keywords": [],
                    "main_topics": [],
                    "cultural_synthesis": "",
                }
            ]
        else:
            logger.info(f"Slang analysis found for country {country}.")

        slang_context = f"""
            Frases representativas: {', '.join(slang_context[0].representative_phrases)}
            Palabras clave: {', '.join(slang_context[0].keywords)}
            Tópicos principales: {', '.join(slang_context[0].main_topics)}
            Síntesis cultural: {slang_context[0].cultural_synthesis}
        """
        # room variables
        room_name = group_context.room.name
        room_description = group_context.room.description
        room_tags = ", ".join(group_context.room.tags)

        # If no prior messages, skip summarization
        if not messages:
            logger.warning("No messages to summarize.")
            return {
                "conversation_summary": "",
                "question": recent_message,
                "agent_name": group_context.agent_name,
            }

        agent_executor = self.initialize_tool_agent()

        prompt_template = await compile_prompt(
            "personalized_agent_template",
            message_history=messages,
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
            context_country=slang_context,
            room_name=room_name,
            room_description=room_description,
            topics=room_tags,
            current_date=get_current_date(),
            current_time=get_current_hour(),
            recent_message=recent_message,
        )

        backoff = self.INITIAL_BACKOFF_SEC
        last_error: Optional[str] = None

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                if agent_executor:
                    try:
                        tool_raw = await agent_executor.ainvoke({"input": prompt_template})
                        logger.info(
                            f"\n\nRaw response from tool-agent (attempt {attempt}): {tool_raw}\n\n"
                        )
                        suggestion = self._parse_output(tool_raw)
                        if self._is_valid(suggestion):
                            logger.info(f"answer: {suggestion}")
                            return {"answer": suggestion, "error": None}
                    except Exception as e:
                        last_error = f"tool-agent: {e}"
                        logger.warning(f"Tool-agent attempt {attempt} failed: {e}")

                direct_raw = await self.llm_manager.ainvoke(prompt=prompt_template)
                logger.info(
                    f"\n\nRaw response from direct LLM (attempt {attempt}): {direct_raw}\n\n"
                )
                suggestion = self._parse_output(direct_raw)
                if self._is_valid(suggestion):
                    logger.info(f"answer: {suggestion}")
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
        Initializes a LangChain agent with tool support.
        """
        tools = [get_latest_news, search_google]
        try:
            prompt = hub.pull("hwchase17/openai-tools-agent")

            agent = create_tool_calling_agent(
                llm=self.llm_manager.llm, tools=tools, prompt=prompt
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
        Converts the output (dict/str/list) to a single "clean" string
        suitable for display to the user (without 'Final Answer:', without ```json, etc.)
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

        text = re.sub(
            r"^```(?:json|md|markdown)?\s*|\s*```$",
            "",
            text.strip(),
            flags=re.IGNORECASE | re.DOTALL,
        )

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
                    for key in "output", "text", "final_answer":
                        if (
                            key in parsed
                            and isinstance(parsed[key], str)
                            and parsed[key].strip()
                        ):
                            cleaned = parsed[key].strip()
                            break
        except Exception:
            pass

        cleaned = re.sub(
            r"^\s*(final\s*answer|respuesta\s*final)\s*:\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = cleaned.strip().strip('"').strip("'").strip()

        return cleaned

    def _is_valid(self, text: Optional[str]) -> bool:
        """
        Simple validity criterion: non-empty and with a minimum length.
        """
        if not text:
            return False
        if text.lower() in {"(sin sugerencias)", "sin sugerencias"}:
            return False
        return len(text) >= self.MIN_ACCEPTED_LEN
