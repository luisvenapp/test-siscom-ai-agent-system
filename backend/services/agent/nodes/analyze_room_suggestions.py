import json
from typing import Any, Dict, List
from collections import Counter
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from utils.get_prompts import compile_prompt
from services.document_extractor import PostgresDocumentExtractor

logger = get_logger(__name__)

class AnalyzeRoomSuggestionsNode(NodeAbstractClass):
    """
    Node to analyze all stored room suggestions and generate final recommendations and statistics.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---ANALYZING ALL ROOM SUGGESTIONS---")
        
        db_extractor = None
        try:
            db_extractor = PostgresDocumentExtractor()
            # Fetch all records from the rooms_management table
            all_suggestions = db_extractor.get_recent_documents(
                database_name="siscom",
                table_name="rooms_management",
                limit=1000 # A reasonable limit to prevent pulling too much data
            )

            
            if not all_suggestions:
                logger.warning("No room suggestions found in the database to analyze.")
                return {"final_analysis": None, "error": "No suggestions found to analyze."}

            # Initialize counters for global statistics
            all_frequent_words = Counter()
            all_frequent_emojis = Counter()
            all_frequent_hashtags = Counter()
            all_mentioned_users = Counter()

            # Format the suggestions for the prompt
            suggestions_context = []
            for suggestion in all_suggestions:
                # Safely parse JSON fields
                try:
                    topics_suggested = suggestion.get("topics_suggested", "[]")
                    main_topics = suggestion.get("main_topics_discussed", "[]")
                    frequent_words = suggestion.get("frequent_words", "{}")
                    frequent_emojis = suggestion.get("frequent_emojis", "{}")
                    frequent_hashtags = suggestion.get("frequent_hashtags", "{}")
                    mentioned_users = suggestion.get("frequent_mentions", "{}")
                except (json.JSONDecodeError, TypeError):
                    topics_suggested = []
                    main_topics = []
                    frequent_words = {}
                    frequent_emojis = {}
                    frequent_hashtags = {}
                    mentioned_users = {}

                # Update global counters
                all_frequent_words.update(frequent_words)
                all_frequent_emojis.update(frequent_emojis)
                all_frequent_hashtags.update(frequent_hashtags)
                all_mentioned_users.update(mentioned_users)

                suggestions_context.append(
                    f"Analysis for Room ID: {suggestion.get('id')}\n"
                    f"Room Statistics:\n"
                    f"- Main Discussed Topics In the Group: {', '.join(main_topics)}\n"
                    f"- Frequent Words In the Group: {', '.join(list(frequent_words.keys())[:20])}\n\n" # Top 10 words
                    f"Room Suggestion Details from room information:\n"
                    f"- Suggested Name: {suggestion.get('room_name_suggested')}\n"
                    f"- Suggested Topics: {', '.join(topics_suggested)}\n"
                    f"- Justification: {suggestion.get('justification')}\n"
                )

            full_context = "\n\n\n".join(suggestions_context)

            # Get top 20 from aggregated data to pass to the prompt
            top_words = {word: count for word, count in all_frequent_words.most_common(20)}
            top_emojis = {emoji: count for emoji, count in all_frequent_emojis.most_common(20)}
            top_hashtags = {tag: count for tag, count in all_frequent_hashtags.most_common(20)}
            top_users = {user: count for user, count in all_mentioned_users.most_common(20)}

            prompt_template = await compile_prompt(
                "analyze_multiple_room_suggestions",
                suggestions_analysis_context=full_context,
                frequent_words=", ".join(top_words.keys()),
                frequent_emojis=", ".join(top_emojis.keys()),
                frequent_hashtags=", ".join(top_hashtags.keys()),
                frequent_user_mentioned=", ".join(top_users.keys())
            )

            analysis_json_str = await self.llm_manager.ainvoke(prompt=prompt_template)
            final_analysis = json.loads(analysis_json_str.strip("` \n").removeprefix("json\n"))
    
            total_information = {
                "room_statistics": {
                    "frequent_words": top_words,
                    "frequent_emojis": top_emojis,
                    "frequent_hashtags": top_hashtags,
                    "mentioned_users": top_users
                },
                "room_suggestions": final_analysis
            }

            logger.info(f"Generated final room analysis and recommendations: {final_analysis}")
            return {"room_suggestion": total_information, "error": None}

        except Exception as e:
            logger.error(f"Error analyzing room suggestions: {e}")
            return {"room_suggestion": {"room_statistics": {}, "room_suggestions": {}}, "error": str(e)}
        finally:
            if db_extractor:
                db_extractor.close_all_connections()