from services.agent.nodes.summarize_content import SummarizeConversationNode
from services.agent.nodes.retrieve_context import RetrieveContextNode
from services.agent.nodes.llm_response_with_context import LLMResponseWithContextNode
from services.agent.nodes.google_search import GoogleResearchNode
from services.agent.nodes.orchestractor import OrchestrationNode
from services.agent.nodes.validator import ValidationNode
from services.agent.nodes.slang_analysis import SlangAnalysisNode
from services.agent.nodes.get_room_info import GetRoomInfoNode
from services.agent.nodes.personalize_agent import PersonalizeNode
from services.agent.nodes.agent_reply_splitter import AgentReplySplitterNode
from services.agent.nodes.speech_validator import SpeechValidatorNode
from services.agent.nodes.generate_suggestions import GenerateTopicSuggestionsNode
from services.agent.nodes.generate_message_suggestions import GenerateMessageSuggestionsNode
from services.agent.nodes.extract_frequent_words import ExtractFrequentWordsNode
from services.agent.nodes.extract_frequent_emojis import ExtractFrequentEmojisNode
from services.agent.nodes.extract_frequent_hashtags import ExtractFrequentHashtagsNode
from services.agent.nodes.extract_mentioned_users import ExtractMentionedUsersNode
from services.agent.nodes.analyze_main_topic import AnalyzeMainTopicNode
from services.agent.nodes.generate_room_suggestion import GenerateRoomSuggestionNode
from services.agent.nodes.analyze_room_suggestions import AnalyzeRoomSuggestionsNode
from services.agent.nodes.rule_creation_wizard import RuleCreationWizardNode


NODES_CLASSES = {
    "summarize_content": SummarizeConversationNode,
    "google_research": GoogleResearchNode, 
    "retrieve_context": RetrieveContextNode,
    "llm_response_with_context": LLMResponseWithContextNode,
    "orchestration": OrchestrationNode,
    "validator": ValidationNode,
    "get_room_info": GetRoomInfoNode,
    "slang_analysis": SlangAnalysisNode,
    "personalize": PersonalizeNode,
    "agent_reply_splitter": AgentReplySplitterNode,
    "speech_validator": SpeechValidatorNode,
    "generate_topic_suggestions": GenerateTopicSuggestionsNode,
    "generate_message_suggestions": GenerateMessageSuggestionsNode,
    "extract_frequent_words": ExtractFrequentWordsNode,
    "extract_frequent_emojis": ExtractFrequentEmojisNode,
    "extract_frequent_hashtags": ExtractFrequentHashtagsNode,
    "extract_mentioned_users": ExtractMentionedUsersNode,
    "analyze_main_topic": AnalyzeMainTopicNode,
    "generate_room_suggestion": GenerateRoomSuggestionNode,
    "analyze_room_suggestions": AnalyzeRoomSuggestionsNode,
    "rule_creation_wizard": RuleCreationWizardNode,
}
