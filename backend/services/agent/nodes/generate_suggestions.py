from typing import Any, Dict, List
import json
from core.logging_config import get_logger
from langchain_core.prompts import ChatPromptTemplate
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message
from schemas.room_info import AgentInfo

from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class GenerateTopicSuggestionsNode(NodeAbstractClass):
    """
    Node responsible for generating topic suggestions based on the conversation context.

    Expects 'messages' in the state as a list of Message objects.
    Outputs a 'suggestions' list of topic strings.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the conversation history and make a routing decision.

        Args:
            state: Dictionary with key 'messages' containing a list of Message objects.

        Returns:
            Updated state with a key 'suggestions' set to a list of topic strings.
        """
        messages: List[Message] = state.get("messages", [])
        group_context = state.get("room_details", "")
        room_info = group_context.room
        topics = room_info.tags
        
        historical_messages = ""
        for message in messages:
            historical_messages += f"{message.sender} ({message.role}): {message.content}\n"

        # If no messages, default to empty suggestions
        if not messages:
            logger.warning("No messages found. Defaulting to empty suggestions.")
            return {"suggestions": []}

        # Compile prompt to determine decision
        prompt_template = await compile_prompt(
            "group_topic_suggester",
            group_topics=", ".join(topics),
            previous_suggested_topics="",
            history_messages=historical_messages
        )

        try:
            suggested_topics = await self.llm_manager.ainvoke(prompt=prompt_template)
            
            try:
                suggested_topics_ = suggested_topics.strip('`').split('\n', 1)[1].rsplit('\n', 1)[0]
                json_response = json.loads(suggested_topics_)
            except json.JSONDecodeError:
                try:
                    json_response = json.loads(suggested_topics)
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON response from LLM.")
                    json_response = []
            logger.info(f"Generated topic suggestions: {json_response}") 
            return {
                "suggestions": json_response,
                "error": None
            }
               
        except Exception as err:
            logger.error(f"An error occurred while generating topic suggestions: {err}")
            return {
                "suggestions": [],
                "error": f"An error occurred while generating topic suggestions: {str(err)}"
            }
