from services.llm_manager import LLMManager
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from schemas.agent import InputState, OutputState
from services.agent.nodes import NODES_CLASSES
# from services.vectorstore_manager import VectorStoreManager
from services.document_extractor import PostgresDocumentExtractor
from conf import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

class MultiAgents:
    """
    Orchestrates the Context Agent workflow
    """

    def __init__(
        self,
        llm_manager: LLMManager,
        # vector_store: VectorStoreManager,
        vector_store: PostgresDocumentExtractor,
    ):

        self.llm_manager = llm_manager
        self.vector_store = vector_store

        kwargs = {
            "llm_manager": llm_manager,
            "vector_store": vector_store,
        }
        self.instatiated_nodes = {
            node_name: getattr(node_class(**kwargs), "execute")
            for node_name, node_class in NODES_CLASSES.items()
        }

    @classmethod
    async def create(cls, model_name: str) -> "MultiAgents":
        """
        Asynchronously creates a new SQLAgentWorkflow instance along with the required SQLAgent.
        """
        llm_manager = LLMManager(model_name)
        vector_store = PostgresDocumentExtractor()
        return cls(llm_manager, vector_store)

    def create_workflow(self) -> StateGraph:
        workflow = StateGraph(
            input=InputState,
            output=OutputState
        )
        
        # 1. Add all nodes
        workflow.add_node("summarize_content", self.instatiated_nodes["summarize_content"])
        workflow.add_node("get_room_info", self.instatiated_nodes["get_room_info"])
        workflow.add_node("slang_analysis", self.instatiated_nodes["slang_analysis"])
        workflow.add_node("orchestrator", self.instatiated_nodes["orchestration"])
        # workflow.add_node("junior", self.instatiated_nodes["junior"])
        # workflow.add_node("senior", self.instatiated_nodes["senior"])
        workflow.add_node("personalize", self.instatiated_nodes["personalize"])
        workflow.add_node("validator", self.instatiated_nodes["validator"])
        workflow.add_node("agent_reply_splitter", self.instatiated_nodes["agent_reply_splitter"])
        workflow.add_node("speech_validator", self.instatiated_nodes["speech_validator"])
        workflow.add_node("generate_topic_suggestions", self.instatiated_nodes["generate_topic_suggestions"])

        # Define execution order. "summarize_content" and "get_room_info" run in parallel.
        workflow.add_edge(START, "summarize_content")
        workflow.add_edge(START, "get_room_info")

        # "slang_analysis" acts as a join point, running after the first two nodes complete.
        workflow.add_edge("get_room_info", "slang_analysis")
        workflow.add_edge("summarize_content", "slang_analysis")

        # After the analysis, the orchestrator decides the next step.
        workflow.add_edge("slang_analysis", "orchestrator")

        # Conditional routing after orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            determine_next_node,
            {
                "personalize": "personalize",
                "__end__": END
            }
        )
        
        # After the junior or senior node, the response must be validated
        # workflow.add_edge("senior", "validator")
        # workflow.add_edge("junior", "validator")
        # workflow.add_edge("personalize", "validator")
        # After personalization, check if it failed and needs a retry.
        workflow.add_conditional_edges(
            "personalize",
            check_personalize_failure,
            {
                "personalize": "personalize",          # Loop back on failure
                "validator": "validator" # Proceed on success
            }
        )
        workflow.add_edge("validator", "speech_validator")
        workflow.add_edge("speech_validator", "agent_reply_splitter")
        workflow.add_edge("agent_reply_splitter", END)

        return workflow

    def create_suggestions_workflow(self) -> StateGraph:
        """
        Creates a dedicated workflow for generating topic suggestions.
        This workflow runs the necessary prerequisite nodes and ends
        after generating the suggestions.
        """
        workflow = StateGraph(
            input=InputState,
            output=OutputState
        )
        
        # 1. Add nodes required for this workflow
        # workflow.add_node("summarize_content", self.instatiated_nodes["summarize_content"])
        workflow.add_node("get_room_info", self.instatiated_nodes["get_room_info"])
        workflow.add_node("generate_topic_suggestions", self.instatiated_nodes["generate_topic_suggestions"])

        # 2. Define execution flow
        # Start with parallel execution of summary and room info fetching
        # workflow.add_edge(START, "summarize_content")
        workflow.add_edge(START, "get_room_info")

        # 3. Join the parallel branches. The 'generate_topic_suggestions' node
        # will wait for both upstream nodes to complete before running.
        # workflow.add_edge("summarize_content", "generate_topic_suggestions")
        workflow.add_edge("get_room_info", "generate_topic_suggestions")

        # 4. End the workflow after suggestions are generated
        workflow.add_edge("generate_topic_suggestions", END)
        return workflow

    def create_message_suggestions_workflow(self) -> StateGraph:
        """
        Creates a dedicated workflow for generating message suggestions.
        This workflow runs the necessary prerequisite nodes and ends
        after generating the suggestions.
        """
        workflow = StateGraph(
            input=InputState,
            output=OutputState
        )
        
        # 1. Add nodes required for this workflow
        workflow.add_node("generate_message_suggestions", self.instatiated_nodes["generate_message_suggestions"])
        workflow.add_node("agent_reply_splitter", self.instatiated_nodes["agent_reply_splitter"])

        # 2. Define execution flow
        # Start with parallel execution of summary and room info fetching
        # workflow.add_edge(START, "summarize_content")
        workflow.add_edge(START, "generate_message_suggestions")

        # 3. Join the parallel branches. The 'generate_topic_suggestions' node
        # will wait for both upstream nodes to complete before running.
        # workflow.add_edge("summarize_content", "generate_topic_suggestions")

        # 4. End the workflow after suggestions are generated
        workflow.add_edge("generate_message_suggestions", "agent_reply_splitter")
        workflow.add_edge("agent_reply_splitter", END)
        # workflow.add_edge("generate_message_suggestions", END)
        return workflow

    def create_room_suggestions_workflow(self) -> StateGraph:
        """
        Creates a dedicated workflow for generating room suggestions based on historical analysis.
        """
        workflow = StateGraph(
            input=InputState,
            output=OutputState
        )
        
        # 1. Add all nodes required for this workflow
        workflow.add_node("get_room_info", self.instatiated_nodes["get_room_info"])
        workflow.add_node("extract_frequent_words", self.instatiated_nodes["extract_frequent_words"])
        workflow.add_node("extract_frequent_emojis", self.instatiated_nodes["extract_frequent_emojis"])
        workflow.add_node("extract_frequent_hashtags", self.instatiated_nodes["extract_frequent_hashtags"])
        workflow.add_node("analyze_main_topic", self.instatiated_nodes["analyze_main_topic"])
        workflow.add_node("extract_mentioned_users", self.instatiated_nodes["extract_mentioned_users"])
        workflow.add_node("generate_room_suggestion", self.instatiated_nodes["generate_room_suggestion"])

        # 2. Define execution flow
        # Start by getting room info.
        workflow.add_edge(START, "get_room_info")
        
        # The following analysis nodes can run in parallel, they depend on the initial state.
        workflow.add_edge(START, "extract_frequent_words")
        workflow.add_edge(START, "extract_frequent_emojis")
        workflow.add_edge(START, "extract_frequent_hashtags")
        workflow.add_edge(START, "analyze_main_topic")
        workflow.add_edge(START, "extract_mentioned_users")

        # 3. Join point: 'generate_room_suggestion' will wait for all its dependencies to complete.
        workflow.add_edge("get_room_info", "generate_room_suggestion")
        workflow.add_edge("extract_frequent_words", "generate_room_suggestion")
        workflow.add_edge("extract_frequent_emojis", "generate_room_suggestion")
        workflow.add_edge("extract_frequent_hashtags", "generate_room_suggestion")
        workflow.add_edge("analyze_main_topic", "generate_room_suggestion")
        workflow.add_edge("extract_mentioned_users", "generate_room_suggestion")

        # 4. End the workflow after the suggestion is generated
        workflow.add_edge("generate_room_suggestion", END)
        return workflow

    def create_final_room_analysis_workflow(self) -> StateGraph:
        """
        Creates a workflow to analyze all stored room suggestions and generate
        a final report with new recommendations and global statistics.
        """
        workflow = StateGraph(
            input=InputState,
            output=OutputState
        )

        # 1. Add the analysis node
        workflow.add_node("analyze_room_suggestions", self.instatiated_nodes["analyze_room_suggestions"])

        # 2. Define execution flow
        workflow.add_edge(START, "analyze_room_suggestions")
        workflow.add_edge("analyze_room_suggestions", END)

        return workflow
    
    def rule_creation_wizard_workflow(self) -> StateGraph:
        """
        Creates a dedicated workflow for generating role creation wizard.
        This workflow runs the necessary prerequisite nodes and ends
        after generating the suggestions.
        """
        workflow = StateGraph(
            input=InputState,
            output=OutputState
        )
        
        # 1. Add nodes required for this workflow
        workflow.add_node("rule_creation_wizard", self.instatiated_nodes["rule_creation_wizard"])
        # workflow.add_node("agent_reply_splitter", self.instatiated_nodes["agent_reply_splitter"])

        # 2. Define execution flow
        # Start with parallel execution of summary and room info fetching
        # workflow.add_edge(START, "summarize_content")
        workflow.add_edge(START, "rule_creation_wizard")

        # 3. Join the parallel branches. The 'generate_topic_suggestions' node
        # will wait for both upstream nodes to complete before running.
        # workflow.add_edge("summarize_content", "generate_topic_suggestions")

        # 4. End the workflow after suggestions are generated
        # workflow.add_edge("rule_creation_wizard", "agent_reply_splitter")
        workflow.add_edge("rule_creation_wizard", END)
        # workflow.add_edge("generate_message_suggestions", END)
        return workflow

    def return_graph(self) -> CompiledStateGraph:
        """
        Compiles and returns the workflow as a runnable graph.
        """
        return self.create_workflow().compile()
    
def determine_next_node(state):
    return state.get("next_node", "__end__")

def check_personalize_failure(state: InputState) -> str:
    """Determines if the personalize node should be retried."""
    if state.get("personalize_failed", False):
        logger.info("Personalize node failed, retrying...")
        return "personalize"  # Route back to the personalize node
    logger.info("Personalize node succeeded, continuing to validator.")
    return "validator" # Continue to the next step
