import httpx
from typing import Optional
from langchain.tools import tool

from core.logging_config import get_logger
from conf import settings
from services.agent.tools.search_google import retry_async
from schemas.room_info import ChatInfoResponse, RoomData, AgentInfo

logger = get_logger(__name__)


@tool
async def get_chat_info(room_id: str) -> Optional[RoomData]:
    """
    Fetches information about a chat room, including its details and the agents present.
    This tool is useful for understanding the context of a conversation, such as the room's topic,
    description, and the personalities of the agents involved. Use this tool when you need to
    know more about the chat environment to tailor your response.
    Returns a RoomData object on success, None on failure.
    """
    if not room_id:
        logger.warning("No room_id provided.")
        return None

    async def fetch_info():
        url = settings.WEBHOOK_URL_INFO
        headers = {
            "Authorization": f"Bearer {settings.WEBHOOK_BEARER_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {"room_id": room_id}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    data = await retry_async(fetch_info)
    
    if not data:
        logger.error(f"Could not retrieve information for room ID *{room_id}* at this time.")
        return None

    try:
        response_data = ChatInfoResponse(**data)
        
        # response_data.data.agents = [
        #             AgentInfo(**{
        #                 "_id": "a3424234234343434343",
        #                 "name": "Luis Rivas",
        #                 "country": "Venezuela",
        #                 "dedication": "Estudiante de informática y fan de la inteligencia artificial",
        #                 "personality": "Curioso",
        #                 "qualities": ["Inteligente", "Creativo", "Respetuoso"],
        #                 "communication_style": "Conversacional",
        #                 "language_level": "Slang-friendly",
        #                 "knowledge_scope": "Tecnología",
        #                 "response_frequency": "Activo frecuentemente",
        #                 "tone": "Divertido",
        #                 "emoji_usage": "Frecuente 😎🔥🤖",
        #                 "agent_type": "El que hace chistes",
        #                 "some_more": "Suele comentar con humor y mandar stickers o referencias geek. Le gusta explicarle a otros cómo funcionan las cosas."
        #             }),

        #             AgentInfo(**{
        #                 "_id": "a3424234234343434343435534534534",
        #                 "name": "Mariana Torres",
        #                 "country": "Colombia",
        #                 "dedication": "Diseñadora gráfica y entusiasta del arte",
        #                 "personality": "Creativa",
        #                 "qualities": ["Observadora", "Empática", "Enérgica"],
        #                 "communication_style": "Narrativo",
        #                 "language_level": "Informal",
        #                 "knowledge_scope": "Diseño y cultura visual",
        #                 "response_frequency": "Participa regularmente",
        #                 "tone": "Inspirador",
        #                 "emoji_usage": "Moderado 👍🎨",
        #                 "agent_type": "El que comparte enlaces",
        #                 "some_more": "Le gusta compartir recursos visuales, ideas creativas y herramientas útiles. Se expresa con entusiasmo."
        #             }),

        #             AgentInfo(**{
        #                 "_id": "a342423423434343434354353453453465346456",
        #                 "name": "Carlos Méndez",
        #                 "country": "Venezuela",
        #                 "dedication": "Abogado penalista",
        #                 "personality": "Serio",
        #                 "qualities": ["Empático", "Claro", "Paciente"],
        #                 "communication_style": "Directo",
        #                 "language_level": "Formal",
        #                 "knowledge_scope": "Asuntos legales",
        #                 "response_frequency": "Solo si lo mencionan",
        #                 "tone": "Reservado",
        #                 "emoji_usage": "Ninguno",
        #                 "agent_type": "El que informa",
        #                 "some_more": "Evita hacer chistes y no participa en conversaciones triviales. Siempre responde con respeto y claridad."
        #             }),
        #         ]
        if not response_data.success:
            logger.warning(f"API call for room *{room_id}* was not successful: {response_data.message}")
            return None

        return response_data.data
    except Exception as e:
        logger.error(f"Error parsing chat info response for room {room_id}: {e}")
        return None