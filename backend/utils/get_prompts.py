import asyncio

from langfuse import Langfuse
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from conf import settings


langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )

async def compile_prompt(prompt_name: str, **kwargs) -> ChatPromptTemplate:
    """
    Asynchronously fetches and compiles a Langfuse prompt with given variables.

    Args:
        prompt_name (str): Name of the prompt in Langfuse.
        **kwargs: Template variables like summarize_style, chat_history, etc.

    Returns:
        ChatPromptTemplate: A ChatPromptTemplate object with compiled messages.
    """
    def _get_and_compile():
        prompt = langfuse.get_prompt(prompt_name, label=settings.LANGFUSE_LABEL)
        return prompt.compile(**kwargs)
    
    compiled_prompt = await asyncio.to_thread(_get_and_compile)
    messages: list[BaseMessage] = []
    for msg in compiled_prompt:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            messages.append(SystemMessage(content=content))
        elif role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    prompt_template = ChatPromptTemplate.from_messages(messages)
    return prompt_template
