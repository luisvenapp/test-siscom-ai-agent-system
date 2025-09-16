from services.llm_manager import LLMManager
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from schemas.action import ActionInputState, ActionOutputState
from services.agent.nodes.actions import ACTION_NODE_CLASSES


class ActionAgent:
    """
    Orchestrates the Context Agent workflow
    """

    def __init__(
        self,
        llm_manager: LLMManager,
    ):
        self.llm_manager = llm_manager

        kwargs = {
            "llm_manager": llm_manager,
        }
        self.instatiated_nodes = {
            node_name: getattr(node_class(**kwargs), "execute")
            for node_name, node_class in ACTION_NODE_CLASSES.items()
        }

    @classmethod
    async def create(cls, model_name: str) -> "ActionAgent":
        """
        Asynchronously creates a new SQLAgentWorkflow instance along with the required SQLAgent.
        """
        llm_manager = LLMManager(model_name)
        return cls(llm_manager)

    def create_workflow(self) -> StateGraph:
        workflow = StateGraph(
            input=ActionInputState,
            output=ActionOutputState
        )

        workflow.add_node(
            "write",
            self.instatiated_nodes["write"]
        )

        workflow.add_node(
            "summarize",
            self.instatiated_nodes["summarize"]
        )

        workflow.add_node(
            "translate",
            self.instatiated_nodes["translate"]
        )

        workflow.add_conditional_edges(
            START,
            lambda state: state["action"],
            {
                "write": "write",
                "summarize": "summarize",
                "translate": "translate",
            }
        )

        # 4. Add edges to connect nodes.
        workflow.add_edge("write", END)
        workflow.add_edge("summarize", END)
        workflow.add_edge("translate", END)

        return workflow

    def return_graph(self) -> CompiledStateGraph:
        """
        Compiles and returns the workflow as a runnable graph.
        """
        return self.create_workflow().compile()
