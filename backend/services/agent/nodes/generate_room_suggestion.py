from typing import Any, Dict, List
import json
from datetime import datetime
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.agent import RoomsCreated
from schemas.message import Message
from utils.get_prompts import compile_prompt
from services.document_extractor import PostgresDocumentExtractor

logger = get_logger(__name__)

class GenerateRoomSuggestionNode(NodeAbstractClass):
    """
    Node to generate a new room suggestion based on conversational analysis.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---GENERATING ROOM SUGGESTION---")
        frequent_words = state.get("frequent_words", [])
        frequent_emojis = state.get("frequent_emojis", [])
        frequent_hashtags = state.get("frequent_hashtags", [])
        main_topic = state.get("main_topics_group", [])
        mentioned_users = state.get("mentioned_users", [])
        rooms_created: List[RoomsCreated] = state.get("rooms_created", [])
        messages: List[Message] = state.get("messages", [])
        previous_rooms: List[str] = state.get("previous_rooms", [])
        
        historical_messages = ""
        for message in messages:
            historical_messages += f"{message.sender} ({message.role}): {message.content}\n"

        rooms_created_str = ""
        if rooms_created:
            room_strs = [f"Name: {room.room_name}, Description: {room.room_description}, Topics: {', '.join(room.room_topics)}" for room in rooms_created]
            rooms_created_str = "\n".join(room_strs)

        prompt_template = await compile_prompt(
            "generate_room_suggestion_from_analysis",
            main_topic=main_topic,
            frequent_words=", ".join(frequent_words),
            frequent_emojis=", ".join(frequent_emojis),
            frequent_hashtags=", ".join(frequent_hashtags),
            mentioned_users=", ".join(mentioned_users),
            existing_rooms=rooms_created_str,
            previous_rooms=", ".join(previous_rooms),
            history_messages=historical_messages
        )
        
        suggestion = {}
        try:
            suggestion_json_str = await self.llm_manager.ainvoke(prompt=prompt_template)
            suggestion = json.loads(suggestion_json_str.strip("` \n").removeprefix("json\n"))
            
            suggestion['frequent_words'] = frequent_words
            suggestion['frequent_emojis'] = frequent_emojis
            suggestion['frequent_hashtags'] = frequent_hashtags
            suggestion['main_topic'] = main_topic
            suggestion['mentioned_users'] = mentioned_users
            
            logger.info(f"Generated room suggestion: {suggestion}")

            # --- Store the suggestion in the database ---
            db_extractor = None
            try:
                db_extractor = PostgresDocumentExtractor()
                room_id = state.get("room_id")

                # Prepare data for insertion, mapping keys to table columns
                data_to_insert = {
                    "id": room_id,
                    "room_name_suggested": suggestion.get("room_name_suggested"),
                    "topics_suggested": json.dumps(suggestion.get("topics", [])),
                    "justification": suggestion.get("justification"),
                    "created_at": datetime.now(),
                    "frequent_words": json.dumps(suggestion.get("frequent_words", {})),
                    "frequent_emojis": json.dumps(suggestion.get("frequent_emojis", {})),
                    "frequent_mentions": json.dumps(suggestion.get("mentioned_users", {})),
                    "frequent_hashtags": json.dumps(suggestion.get("frequent_hashtags", {})),
                    "main_topics_discussed": json.dumps(suggestion.get("main_topic", [])),
                }

                db_extractor.insert_document(
                    database_name="siscom",
                    table_name="rooms_management",
                    data=data_to_insert,
                    conflict_target="id"
                )
                logger.info(f"Successfully stored room suggestion for room_id: {room_id}")
            except Exception as db_error:
                logger.error(f"Failed to store room suggestion in database: {db_error}")

            finally:
                if db_extractor:
                    db_extractor.close_all_connections()

            return {"room_suggestion": suggestion, "error": None}
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error generating or parsing room suggestion: {e}")
            return {"room_suggestion": None, "error": str(e)}