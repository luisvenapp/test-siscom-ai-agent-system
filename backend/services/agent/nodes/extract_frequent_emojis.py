from typing import Any, Dict, List
from collections import Counter
import emoji
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message

logger = get_logger(__name__)

class ExtractFrequentEmojisNode(NodeAbstractClass):
    """
    Node to extract the most frequent emojis from historical messages.
    Note: This node requires the 'emoji' library.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---EXTRACTING FREQUENT EMOJIS---")
        messages: List[Message] = state.get("messages", [])
        if not messages:
            logger.warning("No historical messages found to extract emojis.")
            return {"frequent_emojis": []}
        all_text = " ".join([msg.content for msg in messages])
        emojis_found = [c for c in all_text if c in emoji.EMOJI_DATA]
        emoji_counts = Counter(emojis_found)
        emoji_counts = dict(emoji_counts.most_common(30))
        # most_common_emojis = [emoji for emoji, count in emoji_counts.most_common(10)]
        logger.info(f"Most common emojis: {emoji_counts}")
        return {"frequent_emojis": emoji_counts}