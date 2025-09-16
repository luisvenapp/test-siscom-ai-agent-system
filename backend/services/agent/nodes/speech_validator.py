from typing import Any, Dict, List

from core.logging_config import get_logger
from services.agent.nodes.base import NodeAbstractClass
from utils.get_prompts import compile_prompt

logger = get_logger(__name__)

class SpeechValidatorNode(NodeAbstractClass):
    """
    Node to refine and polish the response from the personalize agent.
    It ensures the answer aligns perfectly with the agent's defined personality,
    tone, and style.
    """

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refines the agent's response to match its personality.

        Args:
            state: Dictionary with keys 'answer', 'room_details', and 'agent_id_executed'.

        Returns:
            Updated state with a polished 'answer'.
        """
        logger.info("---VALIDATING AND REFINING AGENT SPEECH---")
        draft_answer: str = state.get("answer", "")
        group_context = state.get("room_details", "")
        personalize_agent = state.get("personalize_agent", "")
        personality = personalize_agent.get("personality", "").lower().strip()
        slang_context_list = state.get("slang_context", [])
        messages: List[str] = state.get("messages", [])
        
        if not draft_answer:
            logger.warning("No draft answer to validate. Skipping speech validation.")
            return {"answer": ""}

        try:
            # Find the agent that was executed
            agent_to_execute = [agent for agent in group_context.agents if agent.id == personalize_agent.get("id", "")][0]

            previous_messages_agent = [
                f"{msg.sender}: {msg.content}" for msg in messages if msg.user_id == agent_to_execute.id
            ][-3:]
            
            previous_messages_agent = "\n\n".join(previous_messages_agent[::-1])
            
            logger.info(f"Previous messages from agent: {previous_messages_agent}")
            
            if not agent_to_execute:
                logger.error(f"Could not find agent with ID {personalize_agent.get('id', '')} to refine speech.")
                return {"answer": draft_answer}

            # Extract agent details
            agent_name = agent_to_execute.name
            dedication = agent_to_execute.dedication
            qualities = agent_to_execute.qualities
            communication_style = agent_to_execute.communication_style
            tone = agent_to_execute.tone
            emoji_usage = agent_to_execute.emoji_usage
            country = agent_to_execute.country

            # Find the relevant slang context for the agent's country
            slang_for_country = next((analysis for analysis in slang_context_list if analysis.country == country), None)
            
            slang_context_str = "No specific slang context available."
            if slang_for_country:
                slang_context_str = f"""
                    Country: {country}
                    Representative Phrases: {', '.join(slang_for_country.representative_phrases)}
                    Keywords: {', '.join(slang_for_country.keywords)}
                    Main Topics: {', '.join(slang_for_country.main_topics)}
                    Cultural Synthesis: {slang_for_country.cultural_synthesis}
                """
                
                logger.info(f"Slang context: {slang_context_str}")
                
            agent_personality = (
                f"Agent Name: {agent_name}\n"
                f"Agent Country: {country}\n"
                f"Agent Dedication: {dedication}\n"
                f"Agent Qualities: {qualities}\n"
                f"Agent Communication Style: {communication_style}\n"
                f"Agent Tone: {tone}\n"
                f"Agent Emoji Usage: {emoji_usage}\n"
            )
            
            logger.info(f"Agent Personality: {agent_personality}")

            prompt_template = await compile_prompt(
                "speech_validator",
                agent_personality=agent_personality,
                slang_context=slang_context_str,
                agent_answer=draft_answer,
                previous_answers=previous_messages_agent,
            )

            refined_answer = await self.llm_manager.ainvoke(prompt=prompt_template)
            refined_answer = refined_answer.replace("pa'", "pa").replace("Pa'", "pa").replace("¿", "").strip()
            logger.info(f"Refined Answer: {refined_answer}")
            return {"answer": refined_answer.strip()}

        except Exception as err:
            logger.error(f"Error in SpeechValidatorNode: {err}")
            # Return the original answer if refinement fails
            return {"answer": draft_answer}

