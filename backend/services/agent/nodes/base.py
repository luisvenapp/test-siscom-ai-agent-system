from abc import ABC, abstractmethod
from core.logging_config import get_logger
from services.llm_manager import LLMManager

logger = get_logger(__name__)


class NodeAbstractClass(ABC):
    """
    Abstract base class for LangGraph nodes.

    This class defines the interface that all LangGraph nodes must implement.
    It enforces that every node provides an asynchronous `execute` method to process and update
    the state dictionary. Additionally, it initializes a language model manager (LLMManager) 
    to assist with language model operations.
    """

    def __init__(self, llm_manager: LLMManager = None, *args, **kwargs):
        """
        Constructor for NodeAbstractClass.

        Initializes the language model manager. If no LLMManager is provided, a default instance
        is created.

        Args:
            llm_manager (LLMManager, optional): An instance of LLMManager for language model interactions.
                Defaults to None, in which case a new LLMManager is instantiated.
        """
        self.llm_manager = llm_manager

    @abstractmethod
    async def execute(self, state: dict) -> dict:
        """
        Asynchronously process the provided state and return the updated state.

        Each concrete node class must override this method with its specific logic to manipulate
        the state. This method receives a dictionary representing the current state and is expected
        to return a modified version of that state.

        Args:
            state (dict): A dictionary containing the current state information for the node.

        Returns:
            dict: The updated state after processing by the node.

        Raises:
            NotImplementedError: If the concrete class does not implement this method.
        """
        raise NotImplementedError(
            "Subclasses must implement the execute method."
        )
