from typing import Any, Dict, List
import json
from core.logging_config import get_logger
from langchain_core.prompts import ChatPromptTemplate
from services.agent.nodes.base import NodeAbstractClass
from schemas.message import Message
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class RuleCreationWizardNode(NodeAbstractClass):
    """
    Node to create a rule in the rule creation wizard.

    Expects 'user_query' and 'uuid' in state and outputs
    'rule_creation_result'.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a rule based on the user's query and the provided UUID.

        Args:
            state: Dictionary containing 'user_query' and 'uuid'.

        Returns:
            Updated state with 'rule_creation_result'.
        """
        user_query = state.get("user_query", "")
        uuid = state.get("uuid", "")

        # Implement rule creation logic here
        rule_creation_result = f"Rule created for query: {user_query} with UUID: {uuid}"
        
        prompt_template = await compile_prompt(
                "rule_creation_wizard",
                user_query=user_query,
            )

        for attempt in range(3):
            try:
                rule_creation_result = await self.llm_manager.ainvoke(
                    prompt=prompt_template
                )
                try:
                    rule_creation_result_ = rule_creation_result.strip('`').split('\n', 1)[1].rsplit('\n', 1)[0]
                    json_response = json.loads(rule_creation_result_)
                except Exception:
                    json_response = json.loads(rule_creation_result)

                return {"answer": json_response} # Success, exit loop and return
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/3 failed in RuleCreationWizardNode: {e}")
                if attempt == 2:
                    logger.error(f"All attempts failed in RuleCreationWizardNode. Last error: {e}")
                    return {"answer": {"error": str(e)}}
