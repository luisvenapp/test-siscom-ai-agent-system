import json
from typing import Any, Dict, List
from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class AnalyzeMainTopicNode(NodeAbstractClass):
    """
    Node to analyze historical messages and determine the main topic of conversation using an LLM.
    """
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("---ANALYZING MAIN TOPIC---")
        messages: List[Message] = state.get("messages", [])
        if not messages:
            logger.warning("No historical messages found to analyze topic.")
            return {"main_topic": "General"}
        history = "\n".join([f"{msg.sender}: {msg.content}" for msg in messages])
        prompt_template = await compile_prompt(
            "analyze_main_topic_from_history",
            chat_history=history
        )
        try:
            main_topic = await self.llm_manager.ainvoke(prompt=prompt_template)
            
            try:
                main_topic = main_topic.strip('`').split('\n', 1)[1].rsplit('\n', 1)[0]
                main_topic = json.loads(main_topic)
            except json.JSONDecodeError:
                logger.warning("Failed to parse main topic JSON, using raw response.")
           
            logger.info(f"Analyzed main topic: {main_topic}")
            return {"main_topics_group": main_topic}
        except Exception as e:
            logger.error(f"Error analyzing main topic: {e}")
            return {"main_topics_group": []}