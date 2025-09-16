from typing import Any, Dict, List
from collections import Counter
import re
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message

logger = get_logger(__name__)

# A simple list of stopwords, can be expanded
STOPWORDS = set(["de", "la", "las", "no","que", "el", "en", "y", "a", "los", "del", "se", "con", "por", "un", "para", "una", "su", "al", "lo", "como", "más", "o", "pero", "sus", "le", "ha", "me", "si", "sin", "sobre", "este", "ya", "entre", "cuando", "todo", "esta", "ser", "son", "dos", "también", "fue", "había", "era", "muy", "hasta", "desde", "nos", "mi", "tú", "te", "tu", "es"])

class ExtractFrequentWordsNode(NodeAbstractClass):
    """
    Node to extract the most frequent words from historical messages, excluding common stopwords.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---EXTRACTING FREQUENT WORDS---")
        messages: List[Message] = state.get("messages", [])
        if not messages:
            logger.warning("No historical messages found to extract words.")
            return {"frequent_words": []}
        
        all_text = " ".join([msg.content for msg in messages])
        words = re.findall(r'\b\w+\b', all_text.lower())
        filtered_words = [word for word in words if word not in STOPWORDS and not word.isdigit()]
        word_counts = Counter(filtered_words)
        word_counts = dict(word_counts.most_common(30))

        # most_common_words = [word for word, count in word_counts.most_common(30)]
        logger.info(f"Extracted frequent words")
        return {"frequent_words": word_counts}