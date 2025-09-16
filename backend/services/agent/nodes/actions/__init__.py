from services.agent.nodes.actions.write_node import WriteNode
from services.agent.nodes.actions.summarize_node import SummarizeTextNode
from services.agent.nodes.actions.translate_node import TranslateNode

ACTION_NODE_CLASSES = {
    "write": WriteNode,
    "summarize": SummarizeTextNode,
    "translate": TranslateNode,
}
