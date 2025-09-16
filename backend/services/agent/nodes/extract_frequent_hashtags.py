from typing import Any, Dict, List
from collections import Counter
import re
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message

logger = get_logger(__name__)

class ExtractFrequentHashtagsNode(NodeAbstractClass):
    """
    Node to extract the most frequent hashtags from historical messages.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---EXTRACTING FREQUENT HASHTAGS---")
        messages: List[Message] = state.get("messages", [])
        if not messages:
            logger.warning("No historical messages found to extract hashtags.")
            return {"frequent_hashtags": []}
        all_text = " ".join([msg.content for msg in messages])
        hashtags = re.findall(r'#(\w+)', all_text.lower())
        hashtags = [f"#{hashtag}" for hashtag in hashtags]  # Filter out single character hashtags
        hashtag_counts = Counter(hashtags)
        hashtag_counts = dict(hashtag_counts.most_common(30))
        # most_common_hashtags = [hashtag for hashtag, count in hashtag_counts.most_common(10)]
        logger.info(f"Most common hashtags: {hashtag_counts}")
        return {"frequent_hashtags": hashtag_counts}