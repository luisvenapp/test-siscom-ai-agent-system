from typing import Any, Dict
from core.logging_config import get_logger
from langchain_core.prompts import ChatPromptTemplate
from services.agent.nodes.base import NodeAbstractClass
from schemas.agent import (
    SSEResponse,
    StreamingDataTypeEnum,
    StreamingSignalsEnum,
)
import asyncio
from conf import settings

logger = get_logger(__name__)

# Prompt messages for the "write" action using snake_case placeholders
WRITE_PROMPT_MESSAGES = [
    (
        "system",
        """
You are an AI assistant expert at transforming user ideas into fully fleshed-out texts.  
Your instructions:  
1. Receive a user-provided idea and generate a text using the exact style `{write_type}` and tone `{write_tone}`.  
2. Never introduce information beyond what's contained in the original idea.  
3. Strictly adhere to the specified style and tone in choice of words, structure, and nuances.  
4. Automatically detect the language of the user's input and reply solely in that same language.  
5. Return only the completed text in Markdown format—no code blocks, no additional commentary.  
"""
    ),
    (
        "human",
        "{text}"
    ),
]


class WriteNode(NodeAbstractClass):
    """
    Node to develop a user idea into a styled and toned text.

    Expects in state:
      - 'text': the raw idea to expand
      - 'write_type': the desired writing style (e.g., 'blog post', 'formal letter')
      - 'write_tone': the desired tone (e.g., 'friendly', 'professional')

    Outputs in state:
      - 'redaction': the generated text
    """

    async def execute(self, state: Dict[str, Any], config) -> Dict[str, Any]:
        # Extract input parameters from state
        text = state.get("text", "")
        parameters = state.get("parameters", {})
        write_type = parameters.get("write_type", "")
        write_tone = parameters.get("write_tone", "")
        stream_handler = state.get("stream_handler")

        metadata = {
            "parameters": {
                "writeType": write_type,
                "writeTone": write_tone,
            },
            "userId": state.get("user_id", ""),
            "sessionId": state.get("session_id", ""),
            "runId": state.get("run_id", ""),
        }

        # Build the prompt using the template
        prompt = ChatPromptTemplate.from_messages(WRITE_PROMPT_MESSAGES)

        try:
            # Invoke the LLM with the constructed prompt
            response = ""
            async for token in self.llm_manager.astream(
                prompt=prompt,
                text=text,
                write_type=write_type,
                write_tone=write_tone,
                config=config
            ):
                await stream_handler.queue.put(
                    SSEResponse(
                        dataType=StreamingDataTypeEnum.LLM,
                        data=token,
                    )
                )
                await asyncio.sleep(settings.LLM_RESPONSE_DELAY)
                response += token

            await stream_handler.queue.put(
                SSEResponse(
                    data=StreamingSignalsEnum.LLM_END.value,
                    dataType=StreamingDataTypeEnum.SIGNAL,
                )
            )
            await asyncio.sleep(0.1)
            await stream_handler.queue.put(
                SSEResponse(
                    data=StreamingSignalsEnum.END.value,
                    dataType=StreamingDataTypeEnum.SIGNAL,
                    metadata=metadata,
                )
            )
            await asyncio.sleep(0.1)
            stream_handler.done.set()

            logger.info("Generated redaction.")
            return {"answer": response}
        except Exception as err:
            logger.error(f"Error generating redaction: {err}")
            # Return empty string on error
            return {"answer": ""}
