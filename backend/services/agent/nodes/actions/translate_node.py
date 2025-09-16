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

# Prompt messages for the "translate" action using snake_case placeholders
TRANSLATE_PROMPT_MESSAGES = [
    (
        "system",
        """
You are an AI assistant specialized in translation.
Translate the following text from {translate_from} to {translate_to}.
- Preserve meaning exactly.
- Keep formatting as close to the original as possible.
- Return only the translated text, without any additional commentary.
"""
    ),
    (
        "human",
        "{text}"
    ),
]


class TranslateNode(NodeAbstractClass):
    """
    Node to translate text between languages.

    Expects in state:
      - 'text': the text to translate
      - 'translate_from': source language (e.g., 'en')
      - 'translate_to': target language (e.g., 'es')

    Outputs in state:
      - 'translation': the translated text
    """

    async def execute(self, state: Dict[str, Any], config) -> Dict[str, Any]:
        # Extract input parameters from state
        text = state.get("text", "")
        parameters = state.get("parameters", {})
        translate_from = parameters.get("translate_from", "")
        translate_to = parameters.get("translate_to", "")
        stream_handler = state.get("stream_handler")

        metadata = {
            "parameters": {
                "translateFrom": translate_from,
                "translateTo": translate_to,
            },
            "userId": state.get("user_id", ""),
            "sessionId": state.get("session_id", ""),
            "runId": state.get("run_id", ""),
        }

        logger.info(f"Translating from {translate_from} to {translate_to}.")

        # Build the prompt using the template
        prompt = ChatPromptTemplate.from_messages(TRANSLATE_PROMPT_MESSAGES)

        try:
            # Invoke the LLM with the constructed prompt
            response = ""
            async for token in self.llm_manager.astream(
                prompt=prompt,
                text=text,
                translate_from=translate_from,
                translate_to=translate_to,
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
            logger.info("Generated translation.")
            return {"answer": response}
        except Exception as err:
            logger.error(f"Error translating text: {err}")
            # Return empty string on error
            return {"answer": ""}
