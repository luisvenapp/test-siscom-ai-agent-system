from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate

from conf import settings
from core.logging_config import get_logger
from utils.agent import remove_think_content

logger = get_logger(__name__)

class LLMManager:
    """
    Manager for interacting with a language model via ChatLiteLLM.

    Formats prompts, invokes the model asynchronously, and cleans responses.
    """

    def __init__(self, model_name: str = settings.LLM_MODEL_NAME) -> None:
        """
        Initialize LLMManager with the specified model name.

        Args:
            model_name: Identifier of the LLM to use.
        """
        self.model_name = model_name
        self.llm = ChatLiteLLM(model=model_name)

    async def ainvoke(
        self,
        prompt: ChatPromptTemplate,
        response_format: dict | None = None,
        **kwargs,
    ) -> str:
        """
        Asynchronously invoke the LLM with a formatted prompt.
        """
   
        if (
            self.model_name.startswith("ollama")
            and "/" in self.model_name
            and response_format == "json"
        ):
            logger.info(
                f"Using JSON object response format for model: "
                f"{self.model_name}"
            )
        else:
            response_format = None

        messages = prompt.format_messages(**kwargs)
        response = await self.llm.ainvoke(messages, format=response_format)

   
        return remove_think_content(response.content)

    async def astream(
        self,
        prompt: ChatPromptTemplate,
        response_format: dict | None = None,
        **kwargs,
    ) -> str:
        """
        Asynchronously stream the LLM's response.
        """
        if (
            self.model_name.startswith("ollama")
            and "/" in self.model_name
            and response_format == "json"
        ):
            logger.info(
                f"Using JSON object response format for model: "
                f"{self.model_name}"
            )
        else:
            response_format = None

   
        messages = prompt.format_messages(**kwargs)
        async for chunk in self.llm.astream(messages, format=response_format):
            yield chunk.content
