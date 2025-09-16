from typing import Any, Dict

from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from services.agent.tools.get_chat_info import get_chat_info

logger = get_logger(__name__)


class GetRoomInfoNode(NodeAbstractClass):
    """
    A node dedicated to fetching and processing chat room information.
    It uses the `get_chat_info` tool to retrieve details about the room
    and its agents, then populates the state with this context as a RoomData object.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the node's logic to get room information.

        It retrieves the `room_id` from the state, calls the `get_chat_info` tool,
        and stores the returned RoomData object in the 'room_details' key of the state.
        """
        logger.info("---FETCHING ROOM INFORMATION---")
        room_id = state.get("room_id")

        if not room_id:
            logger.warning("No room_id found in state. Skipping room info retrieval.")
            return {"room_details": None}

        try:
            room_info_obj = await get_chat_info.ainvoke(room_id)
            return {"room_details": room_info_obj}
        except Exception as e:
            logger.error(f"Error executing get_chat_info tool: {e}")
            return {"room_details": None}