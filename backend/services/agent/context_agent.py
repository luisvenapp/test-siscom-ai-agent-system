from services.llm_manager import LLMManager
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from schemas.agent import InputState, OutputState
from services.agent.nodes import NODES_CLASSES
# from services.vectorstore_manager import VectorStoreManager
from services.document_extractor import PostgresDocumentExtractor
from conf import settings

class ContextAgent:
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
    async def create(cls, model_name: str) -> "ContextAgent":
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
        workflow.add_node("google_research", self.instatiated_nodes["google_research"])
        workflow.add_node("retrieve_context", self.instatiated_nodes["retrieve_context"])
        workflow.add_node("llm_response_with_context", self.instatiated_nodes["llm_response_with_context"])

        # 2. Define edges (execution order)
        workflow.add_edge(START, "summarize_content")
        workflow.add_edge("summarize_content", "google_research")
        workflow.add_edge("google_research", "retrieve_context")
        workflow.add_edge("retrieve_context", "llm_response_with_context")
        workflow.add_edge("llm_response_with_context", END)

        # 5. Set the entry point.
        workflow.set_entry_point("summarize_content")

        return workflow

    def return_graph(self) -> CompiledStateGraph:
        """
        Compiles and returns the workflow as a runnable graph.
        """
        return self.create_workflow().compile()
