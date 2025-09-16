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

# Prompt messages for the "summarize" action using snake_case placeholders
SUMMARY_PROMPT_MESSAGES = [
    (
        "system",
        """
You are an AI assistant expert at summarizing user-provided texts.  
Your instructions:  
1. Receive a text from the user and produce a summary in the exact style `{summarize_style}`.  
2. Never introduce information not found in the original text.  
3. Be concise—include only the key points.  
4. Automatically detect the language of the user's input and reply solely in that same language.  
5. Return only the summary in Markdown format—no code blocks, no additional commentary.  
"""
    ),
    (
        "human",
        "{text}"
    ),
]


class SummarizeTextNode(NodeAbstractClass):
    """
    Node to summarize a block of text in a specified style.

    Expects in state:
      - 'text': the text to summarize
      - 'summarize_style': the summary style (e.g., 'bullet points', 'paragraph')

    Outputs in state:
      - 'summary': the generated summary
    """

    async def execute(self, state: Dict[str, Any], config) -> Dict[str, Any]:
        # Extract input parameters from state
        text = state.get("text", "")
        parameters = state.get("parameters", {})
        summarize_style = parameters.get("summarize_style", "")
        stream_handler = state.get("stream_handler")

        metadata = {
            "parameters": {
                "summarizeStyle": summarize_style,
            },
            "userId": state.get("user_id", ""),
            "sessionId": state.get("session_id", ""),
            "runId": state.get("run_id", ""),
        }

        # Build the prompt using the template
        prompt = ChatPromptTemplate.from_messages(SUMMARY_PROMPT_MESSAGES)

        try:
            # Invoke the LLM with the constructed prompt
            response = ""
            async for token in self.llm_manager.astream(
                prompt=prompt,
                text=text,
                summarize_style=summarize_style,
                config=config,
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

            logger.info("Generated summary.")
            return {"answer": response}
        except Exception as err:
            logger.error(f"Error summarizing text: {err}")
            # Return empty string on error
            return {"answer": ""}
