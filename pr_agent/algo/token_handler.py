from threading import Lock
from math import ceil
import json
import os
import re

from jinja2 import Environment, StrictUndefined
from tiktoken import encoding_for_model, get_encoding

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class ModelTypeValidator:
    @staticmethod
    def is_openai_model(model_name: str) -> bool:
        return 'gpt' in model_name or re.match(r"^o[1-9](-mini|-preview)?$", model_name)
    
    @staticmethod
    def is_anthropic_model(model_name: str) -> bool:
        return 'claude' in model_name


class TokenEncoder:
    _encoder_instance = None
    _model = None
    _using_fallback = False
    _lock = Lock()  # Create a lock object

    @classmethod
    def _get_tokenizer_settings(cls):
        tokenizer_cfg = get_settings().get("tokenizer", {})
        if isinstance(tokenizer_cfg, dict):
            return tokenizer_cfg
        try:
            return dict(tokenizer_cfg)
        except Exception:
            return {}

    @classmethod
    def _resolve_cache_dir(cls) -> str:
        cfg = cls._get_tokenizer_settings()
        cache_dir = cfg.get("cache_dir", "") or os.environ.get("TIKTOKEN_CACHE_DIR", "")
        if cache_dir:
            cache_dir = os.path.abspath(os.path.expanduser(str(cache_dir)))
            os.makedirs(cache_dir, exist_ok=True)
            os.environ["TIKTOKEN_CACHE_DIR"] = cache_dir
        return cache_dir

    @classmethod
    def _offline_only(cls) -> bool:
        return bool(cls._get_tokenizer_settings().get("offline_only", False))

    @classmethod
    def _fallback_to_estimation(cls) -> bool:
        return bool(cls._get_tokenizer_settings().get("fallback_to_estimation", True))

    @classmethod
    def _select_encoding_name(cls, model: str) -> str:
        return "cl100k_base" if "gpt" in model else "o200k_base"

    @classmethod
    def _required_encodings(cls) -> list[str]:
        configured = cls._get_tokenizer_settings().get("required_encodings", ["o200k_base", "cl100k_base"])
        if isinstance(configured, str):
            configured = [configured]
        return [str(name) for name in configured if name]

    @classmethod
    def _tokenizer_cache_has_encoding(cls, cache_dir: str, encoding_name: str) -> bool:
        if not cache_dir:
            return False
        manifest_path = os.path.join(cache_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return False
        try:
            with open(manifest_path, "r", encoding="utf-8") as manifest_file:
                payload = json.load(manifest_file)
            encodings = payload.get("encodings", [])
            return encoding_name in encodings
        except Exception:
            return False

    @classmethod
    def _missing_required_encodings(cls, cache_dir: str) -> list[str]:
        missing: list[str] = []
        for encoding_name in cls._required_encodings():
            if not cls._tokenizer_cache_has_encoding(cache_dir, encoding_name):
                missing.append(encoding_name)
        return missing

    @classmethod
    def _build_fallback_encoder(cls):
        class ApproxEncoder:
            @staticmethod
            def encode(text, disallowed_special=()):  # noqa: ARG004
                # Approximate tokenization for fully offline fallback.
                tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\w\s]", text or "")
                return [0] * len(tokens)

        if not cls._using_fallback:
            get_logger().warning("Tokenizer fallback enabled: using approximate token counting")
            cls._using_fallback = True
        return ApproxEncoder()

    @classmethod
    def get_token_encoder(cls):
        model = get_settings().config.model
        if cls._encoder_instance is None or model != cls._model:  # Check without acquiring the lock for performance
            with cls._lock:  # Lock acquisition to ensure thread safety
                if cls._encoder_instance is None or model != cls._model:
                    cls._model = model
                    cache_dir = cls._resolve_cache_dir()
                    encoding_name = cls._select_encoding_name(cls._model)
                    try:
                        if cls._offline_only():
                            missing_required = cls._missing_required_encodings(cache_dir)
                            if missing_required:
                                raise FileNotFoundError(
                                    f"Offline tokenizer cache incomplete at '{cache_dir or 'unset'}'. "
                                    f"Missing encodings: {', '.join(missing_required)}"
                                )
                            if not cls._tokenizer_cache_has_encoding(cache_dir, encoding_name):
                                raise FileNotFoundError(
                                    f"Offline tokenizer cache miss for '{encoding_name}' at '{cache_dir or 'unset'}'"
                                )
                        cls._encoder_instance = encoding_for_model(cls._model) if "gpt" in cls._model else get_encoding(
                            "o200k_base")
                        cls._using_fallback = False
                    except Exception as e:
                        get_logger().warning(f"Failed to initialize tokenizer for model '{cls._model}': {e}")
                        if cls._fallback_to_estimation():
                            cls._encoder_instance = cls._build_fallback_encoder()
                        else:
                            raise
        return cls._encoder_instance


class TokenHandler:
    """
    A class for handling tokens in the context of a pull request.

    Attributes:
    - encoder: An object of the encoding_for_model class from the tiktoken module. Used to encode strings and count the
      number of tokens in them.
    - limit: The maximum number of tokens allowed for the given model, as defined in the MAX_TOKENS dictionary in the
      pr_agent.algo module.
    - prompt_tokens: The number of tokens in the system and user strings, as calculated by the _get_system_user_tokens
      method.
    """

    # Constants
    CLAUDE_MODEL = "claude-3-7-sonnet-20250219"
    CLAUDE_MAX_CONTENT_SIZE = 9_000_000 # Maximum allowed content size (9MB) for Claude API

    def __init__(self, pr=None, vars: dict = {}, system="", user=""):
        """
        Initializes the TokenHandler object.

        Args:
        - pr: The pull request object.
        - vars: A dictionary of variables.
        - system: The system string.
        - user: The user string.
        """
        self.encoder = TokenEncoder.get_token_encoder()
        
        if pr is not None:
            self.prompt_tokens = self._get_system_user_tokens(pr, self.encoder, vars, system, user)

    def _get_system_user_tokens(self, pr, encoder, vars: dict, system, user):
        """
        Calculates the number of tokens in the system and user strings.

        Args:
        - pr: The pull request object.
        - encoder: An object of the encoding_for_model class from the tiktoken module.
        - vars: A dictionary of variables.
        - system: The system string.
        - user: The user string.

        Returns:
        The sum of the number of tokens in the system and user strings.
        """
        try:
            environment = Environment(undefined=StrictUndefined)
            system_prompt = environment.from_string(system).render(vars)
            user_prompt = environment.from_string(user).render(vars)
            system_prompt_tokens = len(encoder.encode(system_prompt))
            user_prompt_tokens = len(encoder.encode(user_prompt))
            return system_prompt_tokens + user_prompt_tokens
        except Exception as e:
            get_logger().error(f"Error in _get_system_user_tokens: {e}")
            return 0

    def _calc_claude_tokens(self, patch: str) -> int:
        try:
            import anthropic
            from pr_agent.algo import MAX_TOKENS
            
            client = anthropic.Anthropic(api_key=get_settings(use_context=False).get('anthropic.key'))
            max_tokens = MAX_TOKENS[get_settings().config.model]

            if len(patch.encode('utf-8')) > self.CLAUDE_MAX_CONTENT_SIZE:
                get_logger().warning(
                    "Content too large for Anthropic token counting API, falling back to local tokenizer"
                )
                return max_tokens

            response = client.messages.count_tokens(
                model=self.CLAUDE_MODEL,
                system="system",
                messages=[{
                    "role": "user",
                    "content": patch
                }],
            )
            return response.input_tokens

        except Exception as e:
            get_logger().error(f"Error in Anthropic token counting: {e}")
            return max_tokens

    def _apply_estimation_factor(self, model_name: str, default_estimate: int) -> int:
        factor = 1 + get_settings().get('config.model_token_count_estimate_factor', 0)
        get_logger().warning(f"{model_name}'s token count cannot be accurately estimated. Using factor of {factor}")
        
        return ceil(factor * default_estimate)

    def _get_token_count_by_model_type(self, patch: str, default_estimate: int) -> int:
        """
        Get token count based on model type.

        Args:
            patch: The text to count tokens for.
            default_estimate: The default token count estimate.

        Returns:
            int: The calculated token count.
        """
        model_name = get_settings().config.model.lower()
        
        if ModelTypeValidator.is_openai_model(model_name) and get_settings(use_context=False).get('openai.key'):
            return default_estimate

        if ModelTypeValidator.is_anthropic_model(model_name) and get_settings(use_context=False).get('anthropic.key'):
            return self._calc_claude_tokens(patch)
        
        return self._apply_estimation_factor(model_name, default_estimate)
    
    def count_tokens(self, patch: str, force_accurate: bool = False) -> int:
        """
        Counts the number of tokens in a given patch string.

        Args:
        - patch: The patch string.
        - force_accurate: If True, uses a more precise calculation method.

        Returns:
        The number of tokens in the patch string.
        """
        encoder_estimate = len(self.encoder.encode(patch, disallowed_special=()))

        # If an estimate is enough (for example, in cases where the maximal allowed tokens is way below the known limits), return it.
        if not force_accurate:
            return encoder_estimate

        return self._get_token_count_by_model_type(patch, encoder_estimate)
