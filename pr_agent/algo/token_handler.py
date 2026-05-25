import hashlib
import os
import re
from math import ceil
from pathlib import Path
from threading import Lock

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


class ApproximateTokenEncoder:
    """
    Offline fallback encoder for local/intranet models when no tiktoken cache is available.

    It intentionally only estimates token counts. This keeps strict offline deployments from
    contacting public tokenizer URLs during startup or review processing.
    """

    def encode(self, text: str, *args, **kwargs) -> list[int]:
        if not text:
            return []

        ascii_chars = sum(1 for char in text if ord(char) < 128)
        non_ascii_chars = len(text) - ascii_chars
        estimated_tokens = max(1, ceil(ascii_chars / 4) + ceil(non_ascii_chars * 1.5))
        return [0] * estimated_tokens


class TokenEncoder:
    _encoder_instance = None
    _model = None
    _lock = Lock()  # Create a lock object
    _KNOWN_ENCODING_URLS = {
        "o200k_base": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
        "cl100k_base": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
        "p50k_base": "https://openaipublic.blob.core.windows.net/encodings/p50k_base.tiktoken",
        "r50k_base": "https://openaipublic.blob.core.windows.net/encodings/r50k_base.tiktoken",
    }

    @classmethod
    def _resolve_encoding_name(cls, model: str) -> str:
        model_lower = (model or "").lower()
        if model_lower in cls._KNOWN_ENCODING_URLS:
            return model_lower
        if "gpt-4o" in model_lower or re.match(r"^(openai/)?o[1-9](-mini|-preview)?", model_lower):
            return "o200k_base"
        if "gpt" in model_lower:
            return "cl100k_base"
        return "o200k_base"

    @classmethod
    def _get_tiktoken_cache_path(cls, cache_path: Path, encoding_name: str) -> Path | None:
        blob_url = cls._KNOWN_ENCODING_URLS.get(encoding_name)
        if not blob_url:
            return None
        cache_key = hashlib.sha1(blob_url.encode()).hexdigest()
        return cache_path / cache_key

    @classmethod
    def _get_offline_estimate_fallback(cls) -> bool:
        return get_settings().get("tokenizer.offline_estimate_fallback", True)

    @classmethod
    def _get_approximate_encoder(cls, model: str) -> ApproximateTokenEncoder:
        get_logger().warning(
            f"Using approximate offline token counting for {model}. "
            "Prewarm the tiktoken cache for more accurate context sizing."
        )
        return ApproximateTokenEncoder()

    @classmethod
    def _load_from_local_cache(cls, model: str):
        """
        Attempt to load tokenizer from local cache directory

        Args:
            model: Model name to load

        Returns:
            Encoder instance if found in cache, None otherwise
        """
        try:
            local_cache_dir = get_settings().get("tokenizer.local_cache_dir", "")
            enable_local_cache = get_settings().get("tokenizer.enable_local_cache", False)

            if not enable_local_cache or not local_cache_dir:
                return None

            cache_path = Path(local_cache_dir)
            if not cache_path.exists():
                get_logger().warning(f"Local tokenizer cache directory does not exist: {local_cache_dir}")
                return None
            os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(cache_path))

            encoding_name = cls._resolve_encoding_name(model)
            cache_file = cls._get_tiktoken_cache_path(cache_path, encoding_name)
            if cache_file and cache_file.exists():
                get_logger().info(f"Loading tokenizer from local cache: {encoding_name}")
                return get_encoding(encoding_name)

            return None

        except Exception as e:
            get_logger().warning(f"Failed to load tokenizer from local cache: {e}")
            return None

    @classmethod
    def get_token_encoder(cls):
        model = get_settings().config.model
        if cls._encoder_instance is None or model != cls._model:  # Check without acquiring the lock for performance
            with cls._lock:  # Lock acquisition to ensure thread safety
                if cls._encoder_instance is None or model != cls._model:
                    cls._model = model

                    # Try loading from local cache first
                    cls._encoder_instance = cls._load_from_local_cache(cls._model)

                    if cls._encoder_instance is None:
                        # Fall back to standard loading (may download if not cached by tiktoken)
                        fallback_to_download = get_settings().get("tokenizer.fallback_to_download", True)

                        if not fallback_to_download:
                            if cls._get_offline_estimate_fallback():
                                cls._encoder_instance = cls._get_approximate_encoder(cls._model)
                                return cls._encoder_instance

                            raise RuntimeError(
                                f"Tokenizer not available in local cache and download is disabled for {cls._model}. "
                                "Prewarm the tiktoken cache or set tokenizer.offline_estimate_fallback=true."
                            )

                        try:
                            if "gpt" in cls._model:
                                cls._encoder_instance = encoding_for_model(cls._model)
                            else:
                                cls._encoder_instance = get_encoding("o200k_base")
                            get_logger().info(f"Loaded tokenizer using standard method: {cls._model}")
                        except Exception as e:
                            if not fallback_to_download:
                                get_logger().error(
                                    f"Failed to load tokenizer for {cls._model} and fallback_to_download is disabled. "
                                    f"Error: {e}"
                                )
                                raise RuntimeError(
                                    f"Tokenizer not available in local cache and download is disabled. "
                                    f"Please run: python -m pr_agent.algo.tokenizer_manager download --models {cls._model}"
                                )

                            # Final fallback to o200k_base
                            get_logger().warning(f"Failed to load tokenizer for {cls._model}, falling back to o200k_base: {e}")
                            cls._encoder_instance = get_encoding("o200k_base")

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
