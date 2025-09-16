import asyncio
import random
from datetime import datetime
from core.logging_config import get_logger
from langchain_core.prompts import ChatPromptTemplate
from services.agent.nodes.base import NodeAbstractClass
from services.document_extractor import PostgresDocumentExtractor
from schemas.agent import (
    SSEResponse,
    StreamingDataTypeEnum,
    StreamingSignalsEnum,
)
from conf import settings
from utils.get_prompts import compile_prompt
logger = get_logger(__name__)

class LLMResponseWithContextNode(NodeAbstractClass):
    """
    Node that generates a response to any user question, in the same language as the input,
    formatted in Markdown. Uses the additional context and conversation summary when helpful.
    """

    async def execute_test(self, state: dict, config) -> dict:
        prompt = ChatPromptTemplate.from_messages(
            LLM_GROUP_AGENT_PROMPT_MESSAGES
        )

        stream_handler = state.get("stream_handler")

        metadata = {
            "question": state.get("question", ""),
            "conversationSummary": state.get("conversation_summary", ""),
            "additionalContext": state.get("additional_context", ""),
            "userId": state.get("user_id", ""),
            "sessionId": state.get("session_id", ""),
            "runId": state.get("run_id", ""),
        }

        try:

            response = ""

            async for token in self.llm_manager.astream(
                prompt,
                additional_context=state.get("additional_context", ""),
                conversation_summary=state.get("conversation_summary", ""),
                original_question=state.get("question", ""),
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
            logger.info(f"Generated flexible answer: {response}")
            return {"answer": response}
        except Exception as e:
            logger.exception("Error generating flexible answer")
            return {
                "answer": (
                    "Lo siento, algo salió mal al generar la respuesta. "
                    "¿Podrías reformular o proporcionar más detalles?"
                ),
                "error": str(e)
            }
        
    async def execute(self, state: dict, config) -> dict:
        # prompt = ChatPromptTemplate.from_messages(
        #     LLM_GROUP_AGENT_PROMPT_MESSAGES
        # )

        metadata = {
            "question": state.get("question", ""),
            "conversationSummary": state.get("conversation_summary", ""),
            "additionalContext": state.get("additional_context", ""),
            "userId": state.get("user_id", ""),
            "sessionId": state.get("session_id", ""),
            "runId": state.get("uui_id", ""),
        }

        latest_news_summary = state.get("latest_news_summary", "")
        question_answer_summary = state.get("question_answer_summary", "")


        messages = state.get("messages", [])
        messages_bot = "\n\n".join([f"{msg.sender} ({msg.role}): {msg.content}" for msg in messages if msg.role == "assistant"])

        prompt_template = await compile_prompt(
                "chatgroup_conversational_agent",
                current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                chat_name=state.get("room_name", ""),
                chat_description=state.get("chat_description", ""),
                topics=state.get("topics", ""),
                additional_context=state.get("additional_context", ""),
                conversation_summary=state.get("conversation_summary", ""),
                latest_news_summary=latest_news_summary,
                question_answer_summary=question_answer_summary,
                last_agent_responses=messages_bot
                # original_question=state.get("question", ""),
            )
        

        try:
            try:
                response = await self.llm_manager.ainvoke(
                    prompt_template,
                    config=config,
                )
            except:
                try:
                    prompt_template = await compile_prompt(
                        "chatgroup_conversational_agent",
                        current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        chat_name=state.get("room_name", ""),
                        chat_description=state.get("chat_description", ""),
                        topics=state.get("topics", ""),
                        additional_context="",
                        conversation_summary=state.get("conversation_summary", ""),
                        latest_news_summary="\n📌".join(latest_news_summary.split('\n📌')[2:]),
                        question_answer_summary="\n\n".join(question_answer_summary.split('\n\n')[5:]),
                        last_agent_responses=messages_bot
                        # original_question=state.get("question", ""),
                    )

                    response = await self.llm_manager.ainvoke(
                        prompt_template,
                        config=config,
                    )
                except:
                    prompt_template = await compile_prompt(
                        "chatgroup_conversational_agent",
                        current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        chat_name=state.get("room_name", ""),
                        chat_description=state.get("chat_description", ""),
                        topics=state.get("topics", ""),
                        additional_context="",
                        conversation_summary=state.get("conversation_summary", ""),
                        latest_news_summary="\n📌".join(latest_news_summary.split('\n📌')[2:]),
                        question_answer_summary="\n\n".join(question_answer_summary.split('\n\n')[5:]),
                        last_agent_responses="The assistant messages is in 'conversation_summary'"
                        # original_question=state.get("question", ""),
                    )

                    

                    response = await self.llm_manager.ainvoke(
                        prompt_template,
                        config=config,
                    )

            try:
                extractor = PostgresDocumentExtractor()
                extractor.insert_document(
                    database_name="agent_memory",  
                    table_name="responses",            
                    data={
                        "timestamp": datetime.now(),
                        "room_id": state.get("room_id", ""),
                        "user_input": state.get("question", ""),
                        "agent_response": response,
                        "chat_name": state.get("chat_name", "")
                    }
                )
            except:
                pass

            
            # Response Refiner
            prompt_template = await compile_prompt(
                "AgentResponseRefiner",
                agent_response=response,
                last_agent_responses=messages_bot,
                max_topics=random.choice([1, 2]),  
                conversation_summary=state.get("conversation_summary", ""),
                style_target=random.choice(["Corto", "Medio", "Variado"]),
                user_names_in_conversation=", ".join([f"{msg.sender}" for msg in messages if msg.role != "assistant"]),
                relevant_news_topics=latest_news_summary
            )
                    
            response = await self.llm_manager.ainvoke(
                prompt_template,
                config=config,
            )

            logger.info(f"Generated flexible answer: {response}")
            return {"answer": response}
        except Exception as e:
            logger.exception("Error generating flexible answer")
            return {
                "answer": (
                    "Lo siento, algo salió mal al generar la respuesta. "
                    "¿Podrías reformular o proporcionar más detalles?"
                ),
                "error": str(e)
            }
