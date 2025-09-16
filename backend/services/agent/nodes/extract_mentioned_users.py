from typing import Any, Dict, List
from collections import Counter
import re
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message

logger = get_logger(__name__)

class ExtractMentionedUsersNode(NodeAbstractClass):
    """
    Node to extract the most frequently mentioned users from historical messages.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---EXTRACTING MENTIONED USERS---")
        messages: List[Message] = state.get("messages", [])
        if not messages:
            logger.warning("No historical messages found to extract mentions.")
            return {"mentioned_users": []}
        all_text = " ".join([msg.content for msg in messages])
        mentions = re.findall(r'@(\w+)', all_text)
        mention_counts = Counter(mentions)
        mention_counts = dict(mention_counts.most_common(15))
        # most_common_mentions = [mention for mention, count in mention_counts.most_common(10)]
        logger.info(f"Extracted mentioned users")
        return {"mentioned_users": mention_counts}