"""Security module for PR-Agent."""

from pr_agent.security.auth import (
    AuthManager,
    User,
    APIKey,
    auth_manager,
    get_current_user,
    get_current_user_or_api_key,
    require_permission,
    require_role,
    hash_api_key_for_storage,
    generate_secure_token,
)

__all__ = [
    "AuthManager",
    "User",
    "APIKey",
    "auth_manager",
    "get_current_user",
    "get_current_user_or_api_key",
    "require_permission",
    "require_role",
    "hash_api_key_for_storage",
    "generate_secure_token",
]
