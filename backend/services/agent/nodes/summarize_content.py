from typing import Any, Dict, List

from core.logging_config import get_logger
from langchain_core.prompts import ChatPromptTemplate
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class SummarizeConversationNode(NodeAbstractClass):
    """
    Node to summarize past conversation messages into key bullet points.

    Expects 'messages' in state as a list of Message objects and outputs
    'conversation_summary' and 'question'.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize the conversation and extract the user's last question.

        Args:
            state: Dictionary with key 'messages' containing a list of Message objects.

        Returns:
            Updated state with 'conversation_summary' and 'question'.
        """
        messages: List[Message] = state.get("messages", [])
        messages = messages[::-1]
        question: str = ""

        # Extract last message as the question and remove it from history
        if messages:
            question = f"{messages[0].sender} ({messages[0].role}): {messages[0].content}"
            messages = messages[:]

        # Get agent name from chat history
        agent_name = [msg.sender for msg in messages if msg.role == 'assistant'][0] if len([msg.sender for msg in messages if msg.role == 'assistant']) > 0 else "Assistant"

        # If no prior messages, skip summarization
        if not messages:
            logger.warning("No messages to summarize.")
            return {"conversation_summary": "", "question": question, 'agent_name': agent_name}

        # Format messages into a single history string
        try:
            history = "\n".join(f"- {msg.sender} ({msg.role}): {msg.content}" for msg in messages)
        except:
            history = "\n".join(f"- {msg.sender}: {msg.content}" for msg in messages)

        prompt_template = await compile_prompt(
            "summarize_chat_history",
            chat_history=history,
        )

        try:
            summary = await self.llm_manager.ainvoke(
                prompt=prompt_template
            )
            # logger.info(f"Conversation summary: {summary}")
            return {"conversation_summary": summary, "question": question,  'agent_name': agent_name}
        except Exception as err:
            logger.error(f"Error summarizing conversation: {err}")
            return {"conversation_summary": ""}
