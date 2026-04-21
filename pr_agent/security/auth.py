"""
Authentication and security utilities for PR-Agent web platform.

Provides JWT token authentication, API key management, and role-based access control.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from functools import wraps

try:
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# Security configuration
SECRET_KEY = os.getenv("PR_AGENT_SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
if JWT_AVAILABLE:
    pwd_context = CryptContext(
        schemes=["argon2", "bcrypt"],
        deprecated="auto"
    )

# HTTP Bearer token scheme
security = HTTPBearer()


class User:
    """User model for authentication."""

    def __init__(self, username: str, email: str, role: str = "viewer", hashed_password: str = ""):
        self.username = username
        self.email = email
        self.role = role
        self.hashed_password = hashed_password

    def to_dict(self) -> Dict:
        """Convert user to dictionary."""
        return {
            "username": self.username,
            "email": self.email,
            "role": self.role
        }


class APIKey:
    """API key model."""

    def __init__(self, key: str, name: str, permissions: List[str], created_at: datetime):
        self.key = key
        self.name = name
        self.permissions = permissions
        self.created_at = created_at
        self.last_used = None

    def to_dict(self) -> Dict:
        """Convert API key to dictionary."""
        return {
            "key_prefix": self.key[:8] + "...",
            "name": self.name,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None
        }


class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self._default_user_initialized = False

    def _ensure_default_user(self):
        """Lazily initialize default admin user."""
        if not self._default_user_initialized and JWT_AVAILABLE:
            default_password = os.getenv("PR_AGENT_ADMIN_PASSWORD", "admin")
            try:
                self.create_user("admin", "admin@example.com", default_password, "admin")
            except ValueError:
                # User already exists
                pass
            self._default_user_initialized = True

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        if not JWT_AVAILABLE:
            raise RuntimeError("JWT libraries not installed")
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        if not JWT_AVAILABLE:
            return False
        return pwd_context.verify(plain_password, hashed_password)

    def create_user(self, username: str, email: str, password: str, role: str = "viewer") -> User:
        """Create a new user."""
        if username in self.users:
            raise ValueError(f"User {username} already exists")

        hashed_password = self.hash_password(password)
        user = User(username, email, role, hashed_password)
        self.users[username] = user
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        self._ensure_default_user()
        user = self.users.get(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        if not JWT_AVAILABLE:
            raise RuntimeError("JWT libraries not installed")

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify a JWT token and return payload."""
        if not JWT_AVAILABLE:
            return None

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            return None

    def create_api_key(self, name: str, permissions: List[str]) -> str:
        """Create a new API key."""
        key = secrets.token_urlsafe(32)
        api_key = APIKey(key, name, permissions, datetime.now())
        self.api_keys[key] = api_key
        return key

    def verify_api_key(self, key: str) -> Optional[APIKey]:
        """Verify an API key."""
        api_key = self.api_keys.get(key)
        if api_key:
            api_key.last_used = datetime.now()
        return api_key

    def revoke_api_key(self, key: str) -> bool:
        """Revoke an API key."""
        if key in self.api_keys:
            del self.api_keys[key]
            return True
        return False

    def has_permission(self, user_or_key, permission: str) -> bool:
        """Check if user or API key has a specific permission."""
        if isinstance(user_or_key, User):
            # Admin has all permissions
            if user_or_key.role == "admin":
                return True
            # Editor can read and write
            if user_or_key.role == "editor" and permission in ["read", "write"]:
                return True
            # Viewer can only read
            if user_or_key.role == "viewer" and permission == "read":
                return True
            return False
        elif isinstance(user_or_key, APIKey):
            return permission in user_or_key.permissions
        return False


# Global auth manager instance
auth_manager = AuthManager()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> User:
    """Dependency to get current authenticated user from JWT token."""
    if not JWT_AVAILABLE:
        raise HTTPException(status_code=501, detail="Authentication not available")

    token = credentials.credentials
    payload = auth_manager.verify_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = auth_manager.users.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user_or_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Dependency to get current user or API key."""
    token = credentials.credentials

    # Try JWT token first
    if JWT_AVAILABLE:
        payload = auth_manager.verify_token(token)
        if payload:
            username = payload.get("sub")
            user = auth_manager.users.get(username)
            if user:
                return user

    # Try API key
    api_key = auth_manager.verify_api_key(token)
    if api_key:
        return api_key

    raise HTTPException(status_code=401, detail="Invalid authentication credentials")


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if current_user is None:
                raise HTTPException(status_code=401, detail="Authentication required")

            if not auth_manager.has_permission(current_user, permission):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if not isinstance(current_user, User):
                raise HTTPException(status_code=403, detail="User authentication required")

            if current_user.role != role and current_user.role != "admin":
                raise HTTPException(status_code=403, detail=f"Role '{role}' required")

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator


def hash_api_key_for_storage(api_key: str) -> str:
    """Hash API key for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)
