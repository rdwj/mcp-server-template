"""Authentication utilities for MCP servers.

This module provides authentication and authorization helpers for FastMCP servers,
with support for JWT token verification and scope-based access control.

Recommended Patterns (FastMCP v2.11.0+):
    - Use get_token_claims() to access JWT claims
    - Use get_token_scopes() to check user permissions
    - Use @requires_scopes() decorator for tool-level authorization

Legacy Patterns (for custom JWT verification):
    - Use claims_from_ctx() only if you need custom JWT verification
    - Configure via MCP_AUTH_JWT_ALG, MCP_AUTH_JWT_SECRET, MCP_AUTH_JWT_PUBLIC_KEY

Example:
    from core.auth import get_token_claims, requires_scopes

    @mcp.tool
    @requires_scopes("read:data")
    async def get_data() -> dict:
        claims = get_token_claims()
        user_id = claims.get("sub") if claims else None
        return {"user_id": user_id, "data": [...]}
"""

import os
import jwt
from dataclasses import dataclass
from fastmcp import Context
from fastmcp.server.dependencies import get_access_token, AccessToken
from .logging import get_logger

log = get_logger("auth")


@dataclass
class AllowedOrigins:
    patterns: list[str]

    @classmethod
    def from_env(cls, key: str) -> "AllowedOrigins":
        raw = os.getenv(key, "")
        patterns = [p.strip() for p in raw.split(",") if p.strip()]
        return cls(patterns)


class BearerVerifier:
    def __init__(
        self,
        alg: str | None = None,
        secret: str | None = None,
        public_key: str | None = None,
    ) -> None:
        self.alg = alg
        self.secret = secret
        self.public_key = public_key

    @classmethod
    def from_env(cls) -> "BearerVerifier | None":
        alg = os.getenv("MCP_AUTH_JWT_ALG")
        secret = os.getenv("MCP_AUTH_JWT_SECRET")
        public_key = os.getenv("MCP_AUTH_JWT_PUBLIC_KEY")
        if not alg or not (secret or public_key):
            return None
        return cls(alg=alg, secret=secret, public_key=public_key)

    def verify(self, token: str) -> dict | None:
        try:
            if self.public_key:
                return jwt.decode(token, self.public_key, algorithms=[self.alg])
            return jwt.decode(token, self.secret, algorithms=[self.alg])
        except Exception as e:
            log.warning(f"JWT verify failed: {e}")
            return None


def _get_bearer_from_headers(headers: dict[str, str]) -> str | None:
    auth = headers.get("authorization") or headers.get("Authorization")
    if not auth:
        return None
    if not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip()


def get_token_claims() -> dict | None:
    """Get JWT claims from the authenticated access token.

    This is the RECOMMENDED approach for accessing token claims in FastMCP v2.11.0+.
    Uses FastMCP's built-in get_access_token() which works with the framework's
    authentication system.

    Returns:
        dict: JWT claims from the access token, or None if not authenticated

    Example:
        @mcp.tool
        async def my_tool() -> str:
            claims = get_token_claims()
            if not claims:
                return "Not authenticated"
            user_id = claims.get("sub")
            tenant_id = claims.get("tenant_id")
            return f"User {user_id} in tenant {tenant_id}"
    """
    try:
        token: AccessToken | None = get_access_token()
        return token.claims if token else None
    except Exception as e:
        log.warning(f"Failed to get access token: {e}")
        return None


def get_token_scopes() -> set[str]:
    """Get OAuth scopes from the authenticated access token.

    Convenience function to extract scopes from token claims.
    Handles both 'scope' (space-separated string) and 'scopes' (list) claim formats.

    Returns:
        set[str]: Set of scope strings, empty set if not authenticated

    Example:
        @mcp.tool
        async def check_permissions() -> dict:
            scopes = get_token_scopes()
            return {
                "can_read": "read:data" in scopes,
                "can_write": "write:data" in scopes,
                "all_scopes": sorted(scopes)
            }
    """
    try:
        token: AccessToken | None = get_access_token()
        if not token or not token.claims:
            return set()

        # Handle 'scope' as space-separated string
        scope_str = token.claims.get("scope", "")
        scopes_from_string = set(scope_str.split()) if scope_str else set()

        # Handle 'scopes' as list
        scopes_from_list = set(token.claims.get("scopes", []))

        return scopes_from_string | scopes_from_list
    except Exception as e:
        log.warning(f"Failed to get token scopes: {e}")
        return set()


def claims_from_ctx(ctx: Context) -> dict | None:
    """Get JWT claims by manually extracting and verifying Bearer token from headers.

    DEPRECATED: This approach is fragile and should only be used for custom JWT
    verification scenarios. For standard authentication, use get_token_claims() instead.

    This function requires HTTP transport and manual JWT verification via environment
    variables (MCP_AUTH_JWT_ALG, MCP_AUTH_JWT_SECRET or MCP_AUTH_JWT_PUBLIC_KEY).

    Args:
        ctx: FastMCP Context object

    Returns:
        dict: JWT claims if verification succeeds, None otherwise
    """
    try:
        headers = getattr(getattr(ctx, "request", None), "headers", {}) or {}
        token = _get_bearer_from_headers(headers)
        verifier = BearerVerifier.from_env()
        return verifier.verify(token) if (verifier and token) else None
    except Exception:
        return None


def requires_scopes(*scopes: str):
    """Decorator to require specific OAuth scopes for tool access.

    Uses the recommended get_token_scopes() approach with fallback to
    claims_from_ctx() for backward compatibility.

    Args:
        *scopes: Required scope strings. If empty, uses MCP_REQUIRED_SCOPES env var.

    Example:
        @mcp.tool
        @requires_scopes("read:data", "write:data")
        async def secure_operation(ctx: Context) -> str:
            return "Operation completed"
    """
    required = (
        set(scopes)
        if scopes
        else set((os.getenv("MCP_REQUIRED_SCOPES", "").split(",")))
    )
    required = {s.strip() for s in required if s.strip()}

    def deco(fn):
        async def wrapper(*args, **kwargs):
            # Extract Context if provided (for logging and legacy fallback)
            ctx = kwargs.get("ctx") or next(
                (a for a in args if isinstance(a, Context)), None
            )

            # Try recommended approach first (FastMCP v2.11.0+)
            token_scopes = get_token_scopes()

            # Fall back to legacy approach if needed
            if not token_scopes and ctx:
                claims = claims_from_ctx(ctx) or {}
                token_scopes = set((claims.get("scope") or "").split()) | set(
                    claims.get("scopes", [])
                )

            if not required.issubset(token_scopes):
                if ctx:
                    await ctx.error("Forbidden: missing required scopes")
                return {
                    "error": "forbidden",
                    "missing": sorted(required - token_scopes),
                }
            return await fn(*args, **kwargs)

        return wrapper

    return deco
