from nemoguardrails import LLMRails, RailsConfig
from core.logging_config import get_logger
import hashlib
from pathlib import Path
from typing import List, Optional, Tuple

from schemas.room_info import Rules
from services.llm_manager import LLMManager

logger = get_logger(__name__)

class GuardrailsManager:
    """
    Manages NeMo Guardrails for response validation.
    This is implemented as a singleton to avoid re-initializing the rails engine,
    but it caches different rail configurations based on dynamic rules.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GuardrailsManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = "guardrails"):
        # Prevent re-initialization on subsequent calls
        if hasattr(self, 'base_config_path'):
            return
            
        # Correctly resolve the path to the guardrails config directory
        self.base_config_path = Path(__file__).resolve().parent.parent / config_path
        self.base_config = self._load_base_config()

        if self.base_config:
            # Create a hash of the base configuration content to uniquely identify it.
            # This ensures that if the config files change, we create new rail apps
            # instead of using stale cached ones after a restart.
            config_str = (
                self.base_config["yaml"]
                + self.base_config["colang"]
                + self.base_config["prompts"]
            )
            self.base_config_hash = hashlib.md5(config_str.encode()).hexdigest()
        else:
            self.base_config_hash = "no_config"

        self.rails_apps_cache = {}  # Cache for LLMRails instances

    def _load_base_config(self):
        """Loads the base YAML and Colang configurations from files."""
        if not self.base_config_path.exists():
            logger.error(f"Guardrails config path does not exist: {self.base_config_path}")
            return None

        config_file = self.base_config_path / "config.yml"
        colang_file = self.base_config_path / "base.co" 
        prompt_file = self.base_config_path / "prompt.yml"

        if not config_file.exists():
            logger.error(f"Base guardrails config.yml not found in: {self.base_config_path}")
            return None

        try:
            yaml_content = ""
            with open(config_file, "r", encoding="utf-8") as f:
                yaml_content = f.read()

            colang_content = ""
            if colang_file.exists():
                with open(colang_file, "r", encoding="utf-8") as f:
                    colang_content = f.read()

            prompts_content = ""
            if prompt_file.exists():
                with open(prompt_file, "r", encoding="utf-8") as f:
                    prompts_content = f.read()

            return {"yaml": yaml_content, "colang": colang_content, "prompts": prompts_content}
        except Exception as e:
            logger.error(f"Error loading base guardrails configuration: {e}")
            return None

    def _get_or_create_rails_app(self, dynamic_rules: List[Rules], llm_manager: LLMManager):
        """
        Retrieves a cached LLMRails app for a given set of dynamic rules,
        or creates a new one if it doesn't exist.
        """
        if not self.base_config:
            logger.error("Base guardrails configuration not loaded. Cannot create rails app.")
            return None

        # Create a stable cache key from the sorted rule IDs.
        rule_ids = sorted([rule.id for rule in dynamic_rules])
        rule_key = "_".join(rule_ids) if rule_ids else "base"
        # Combine the base config hash with the rule key for a unique cache key.
        cache_key = f"{self.base_config_hash}_{rule_key}"

        if cache_key in self.rails_apps_cache:
            return self.rails_apps_cache[cache_key]

        prompts_template = self.base_config["prompts"]
        placeholder = "{{dynamic_rules_placeholder}}"

        # Find the full line containing the placeholder to determine its indentation
        placeholder_line_full = ""
        for line in prompts_template.split('\n'):
            if placeholder in line:
                placeholder_line_full = line
                break
        
        indentation_level = len(placeholder_line_full) - len(placeholder_line_full.lstrip(' '))
        indent_str = ' ' * indentation_level

        # --- Create dynamic configuration by injecting rules into the prompt YAML ---
        dynamic_prompts_content = prompts_template
        if dynamic_rules:
            # Generate the dynamic rules as a raw text block.
            rules_text_parts = ["Políticas Dinámicas (específicas de esta sala):"]
            for rule in dynamic_rules:
                # The description can have multiple lines. We must preserve them.
                # Replacing colons is a good practice to avoid potential syntax conflicts.
                description = rule.description.replace(':', '. ')
                rules_text_parts.append(f"- {rule.name}: {description}")
            
            raw_rules_block = "\n".join(rules_text_parts)

            # Indent every line of the generated block to match the placeholder's indentation.
            # This ensures the entire block is correctly placed within the YAML literal block scalar.
            indented_rules_block = "\n".join([f"{indent_str}{line}" for line in raw_rules_block.split('\n')])

            # Replace the placeholder in the YAML content
            dynamic_prompts_content = prompts_template.replace(placeholder_line_full, indented_rules_block)
        else:
            # If no dynamic rules, just remove the placeholder line entirely.
            dynamic_prompts_content = prompts_template.replace(placeholder_line_full, "")

        # Combine the base config YAML with the dynamically generated prompts YAML
        full_yaml_content = self.base_config["yaml"] + "\n\n" + dynamic_prompts_content
        try:
            config = RailsConfig.from_content(
                colang_content=self.base_config["colang"],
                yaml_content=full_yaml_content
            )
            app = LLMRails(config, llm=llm_manager.llm)
            logger.info(f"NeMo Guardrails initialized successfully for rule set: '{cache_key}'")
            self.rails_apps_cache[cache_key] = app
            return app
        except Exception as e:
            logger.error(f"Failed to initialize dynamic NeMo Guardrails for rule set '{cache_key}': {e}")
            return None

    async def validate_response(self, question: str, answer: str, llm_manager: LLMManager, context: Optional[str] = None, dynamic_rules: Optional[List[Rules]] = None) -> Tuple[bool, str]:
        """
        Validates a generated response against a set of guardrails.

        Args:
            question: The user's question for context.
            answer: The bot's generated answer to validate.
            context: The conversation summary for additional context.
            dynamic_rules: A list of dynamic rules to apply for this validation.
            llm_manager: The language model manager instance.

        Returns:
            A tuple (is_valid, final_answer). `is_valid` is True if the answer passed.
        """
        rails_app = self._get_or_create_rails_app(dynamic_rules or [], llm_manager)
        if not rails_app:
            logger.warning("Guardrails app not available. Bypassing validation.")
            return True, answer

        try:
            history = [{"role": "user", "content": context}, {"role": "assistant", "content": answer}]
            # Pass the conversation summary as a keyword argument.
            # The key 'conversation_context' becomes a variable in the Colang scope.;
            # import pdb; pdb.set_trace()
            result = await rails_app.generate_async(messages=history
            )
            final_answer = result['content']
            # A simple check: if the answer was changed, it was not "valid" in its original form.
            
            is_valid = (final_answer == answer)
            if not is_valid:
                logger.warning(f"Guardrails blocked/modified response. Original: '{answer}', New: '{final_answer}'")

            return is_valid, final_answer
        except Exception as e:
            logger.error(f"Error during Guardrails validation: {e}")
            # Return False and a safe fallback message.
            return False, "I'm sorry, an error occurred while validating the response."