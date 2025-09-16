from typing import Any, Dict, List
import json
from core.logging_config import get_logger
from langchain_core.prompts import ChatPromptTemplate
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message
from schemas.room_info import AgentInfo

from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class OrchestrationNode(NodeAbstractClass):
    """
    Orchestration node responsible for analyzing the conversation context
    and deciding whether the next task should be handled by the 'junior' or 'senior' node.

    Expects 'messages' in the state as a list of Message objects.
    Outputs a 'decision' string: either 'junior' or 'senior'.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the conversation history and make a routing decision.

        Args:
            state: Dictionary with key 'messages' containing a list of Message objects.

        Returns:
            Updated state with a key 'decision' set to either 'junior' or 'senior'.
        """
        messages: List[Message] = state.get("conversation_summary", [])
        recent_message: str = state.get("question", "")
        group_context = state.get("room_details", "")
        mss: List[Message] = state.get("messages", [])
        
        # If no messages, default to 'junior'
        if not messages:
            logger.warning("No messages found. Defaulting to 'junior' decision.")
            return {"decision": "junior"}

        assistants = [message for message in mss if message.role == "assistant"]
        if assistants:
            last_agent_executed = assistants[-1].sender
            last_agent_id_executed = assistants[-1].user_id

            last_agent = f"{last_agent_executed} (ID: {last_agent_id_executed})"
            
        else:
            last_agent = ""


        agents_in_group = ""
        for i, agent in enumerate(group_context.agents):
            agents_in_group += f"""
            Agent {i+1}:
            
            ID: {agent.id}
            Name: {agent.name}
            Personality: {agent.personality}
            Dedication: {agent.dedication}
            Qualities: {', '.join(agent.qualities)}
            Some More: {agent.some_more}
            Communication Style: {agent.communication_style}
            Language Level: {agent.language_level}
            Knowledge Scope: {agent.knowledge_scope}
            Response Frequency: {agent.response_frequency}
            Tone: {agent.tone}
            Emoji Usage: {agent.emoji_usage}
            Agent Type: {agent.agent_type}
            \n\n"""

        # Compile prompt to determine decision
        prompt_template = await compile_prompt(
            "orchestrator_agent",
            agents_in_group=agents_in_group,
            agents_can_interact=group_context.room.agents_can_interact,
            message_history=messages,
            recent_message=recent_message,
            last_agent_executed=last_agent,
        )
        
        valid_agent_ids = {agent.id for agent in group_context.agents}
        max_retries = 6

        for attempt in range(max_retries):
            try:
                logger.info(f"Orchestration attempt {attempt + 1}/{max_retries}")
                decision = await self.llm_manager.ainvoke(prompt=prompt_template)
                
                logger.info(f"Orchestrator response: {decision}")

                if '__end__' in decision:
                    logger.info("Orchestrator decided to end the conversation.")
                    return {"next_node": "__end__", "agent_id_executed": ""}

                try:
                    decision_clean = decision.strip('`').split('\n', 1)[1].rsplit('\n', 1)[0]
                    json_response = json.loads(decision_clean)
                except:
                    try:
                        decision_clean = decision
                        json_response = json.loads(decision_clean)
                    except json.JSONDecodeError:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to parse JSON from orchestrator. Response: '{decision}'")
                        continue
                    
                agent_id = json_response.get("id", "").lower().strip()
                if agent_id in valid_agent_ids:
                    logger.info(f"Orchestrator made a valid decision: {decision_clean}")
                    return {
                        "next_node": "personalize",
                        "personalize_agent": {
                            "id": agent_id,
                            "personality": json_response.get("personality", "").lower().strip(),
                        },
                        "agent_id_executed": agent_id
                    }
                else:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries}: Invalid agent ID '{agent_id}' returned. Valid IDs: {valid_agent_ids}")
            except Exception as err:
                logger.error(f"An unexpected error occurred during orchestration on attempt {attempt + 1}/{max_retries}: {err}")

        logger.error(f"Orchestrator failed to return a valid agent ID after {max_retries} attempts. Ending execution.")
        return {"next_node": "__end__", "agent_id_executed": ""}
