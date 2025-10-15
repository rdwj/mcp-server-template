"""Runtime dependencies examples for FastMCP v2.2.11+.

This module demonstrates how to use FastMCP's runtime dependency functions
to access context, HTTP information, and authentication tokens from anywhere
in your code, not just in tool function parameters.

Key patterns demonstrated:
- get_context() for accessing context in nested functions
- get_access_token() for authentication and multi-tenancy
- get_http_headers() for safe header access
- get_http_request() for full request details
- Combining multiple runtime dependencies
"""

from fastmcp.server.dependencies import (
    get_context,
    get_access_token,
    get_http_headers,
    get_http_request,
)

from core.logging import get_logger

log = get_logger("tools.runtime_deps")


# Example 1: Using get_context() in utility functions


async def validate_data_internal(data: list[float]) -> dict:
    """Utility function that uses get_context() for logging.

    This function doesn't receive Context as a parameter, but can still
    access it using get_context() runtime dependency.
    """
    # Access context without it being passed as parameter
    ctx = get_context()

    await ctx.info(f"Validating {len(data)} data points")

    if not data:
        await ctx.warning("Empty dataset provided")
        return {"valid": False, "error": "empty dataset"}

    if any(x < 0 for x in data):
        await ctx.warning("Dataset contains negative values")
        return {"valid": False, "error": "negative values"}

    await ctx.debug("Validation passed")
    return {"valid": True, "data_points": len(data)}


async def process_data_internal(data: list[float]) -> dict:
    """Another utility that uses get_context() internally."""
    ctx = get_context()

    await ctx.info("Processing data...")

    total = sum(data)
    mean = total / len(data) if data else 0

    await ctx.debug(f"Calculated mean: {mean}")

    return {"sum": total, "mean": mean, "count": len(data)}


async def analyze_dataset_with_utils(numbers: list[float]) -> dict:
    """Tool that uses utility functions with get_context().

    Shows how utility functions can use context without explicitly
    passing it through the call chain.

    Args:
        numbers: List of numbers to analyze

    Returns:
        dict: Analysis results including validation and statistics
    """
    # Call utility functions that use get_context() internally
    validation = await validate_data_internal(numbers)

    if not validation["valid"]:
        return {"error": validation["error"], "processed": False}

    stats = await process_data_internal(numbers)

    return {
        "processed": True,
        "validation": validation,
        "statistics": stats,
    }


# Example 2: Using get_access_token() for authentication


async def get_current_user_info() -> dict:
    """Get information about the currently authenticated user.

    Demonstrates accessing token claims using get_access_token().

    Returns:
        dict: User information from token or anonymous info
    """
    token = get_access_token()

    if token is None:
        return {
            "authenticated": False,
            "user_type": "anonymous",
        }

    # Extract standard JWT claims
    user_id = token.claims.get("sub")  # Standard subject claim
    email = token.claims.get("email")

    # Extract custom claims for multi-tenancy
    tenant_id = token.claims.get("tenant_id")
    organization = token.claims.get("org") or token.claims.get("organization")
    role = token.claims.get("role")

    return {
        "authenticated": True,
        "user_id": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "organization": organization,
        "role": role,
        "scopes": token.scopes,
        "client_id": token.client_id,
    }


async def check_user_permission(required_scope: str) -> dict:
    """Check if the current user has a required permission.

    Args:
        required_scope: The scope required for the operation

    Returns:
        dict: Permission check result
    """
    token = get_access_token()

    if token is None:
        return {"allowed": False, "reason": "not authenticated"}

    if required_scope in token.scopes:
        return {
            "allowed": True,
            "scope": required_scope,
            "user_id": token.claims.get("sub"),
        }

    return {
        "allowed": False,
        "reason": "insufficient permissions",
        "required": required_scope,
        "available": token.scopes,
    }


# Example 3: Using get_http_headers() for request analysis


async def analyze_client_info() -> dict:
    """Analyze client information from HTTP headers.

    Shows safe header access that won't fail if not in HTTP context.

    Returns:
        dict: Client information extracted from headers
    """
    # Safe header access - returns empty dict if not in HTTP context
    headers = get_http_headers()

    # Extract common headers
    user_agent = headers.get("user-agent", "Unknown")
    accept = headers.get("accept", "Unknown")
    content_type = headers.get("content-type", "Unknown")
    accept_language = headers.get("accept-language", "Unknown")

    # Check for authentication
    has_auth = bool(headers.get("authorization"))
    auth_type = None
    if has_auth:
        auth_header = headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            auth_type = "Bearer"
        elif auth_header.startswith("Basic "):
            auth_type = "Basic"

    return {
        "user_agent": user_agent,
        "accept": accept,
        "content_type": content_type,
        "accept_language": accept_language,
        "has_authentication": has_auth,
        "auth_type": auth_type,
        "total_headers": len(headers),
    }


# Example 4: Using get_http_request() for full request details


async def get_request_metadata() -> dict:
    """Get comprehensive HTTP request metadata.

    Demonstrates accessing the full Starlette Request object.

    Returns:
        dict: Complete request metadata
    """
    request = get_http_request()

    # Extract basic request info
    method = request.method
    url = str(request.url)
    path = request.url.path
    scheme = request.url.scheme

    # Extract client info
    client_ip = request.client.host if request.client else "Unknown"
    client_port = request.client.port if request.client else None

    # Extract query parameters
    query_params = dict(request.query_params)

    return {
        "method": method,
        "url": url,
        "path": path,
        "scheme": scheme,
        "client": {
            "ip": client_ip,
            "port": client_port,
        },
        "query_params": query_params,
        "has_body": request.method in ["POST", "PUT", "PATCH"],
    }


# Example 5: Combining multiple runtime dependencies


async def create_comprehensive_audit_log(action: str, details: dict) -> dict:
    """Create a comprehensive audit log entry.

    Demonstrates combining all runtime dependencies for complete audit tracking.

    Args:
        action: The action being audited
        details: Additional details about the action

    Returns:
        dict: Complete audit log entry
    """
    # Get context for logging
    ctx = get_context()
    await ctx.info(f"Creating audit log for: {action}")

    # Get authentication info
    token = get_access_token()
    user_id = token.claims.get("sub") if token else "anonymous"
    tenant_id = token.claims.get("tenant_id") if token else None

    # Get HTTP request info
    headers = get_http_headers()
    user_agent = headers.get("user-agent", "unknown")
    client_ip = "unknown"

    try:
        request = get_http_request()
        client_ip = request.client.host if request.client else "unknown"
    except Exception:
        # Not in HTTP context, use default
        pass

    # Build complete audit entry
    audit_entry = {
        "action": action,
        "details": details,
        "user": {
            "user_id": user_id,
            "tenant_id": tenant_id,
        },
        "request": {
            "ip": client_ip,
            "user_agent": user_agent,
        },
        "timestamp": "2025-10-15T00:00:00Z",  # In real code, use datetime.utcnow()
    }

    await ctx.debug(f"Audit entry created: {audit_entry}")

    return audit_entry


async def perform_audited_operation(operation: str, data: str) -> dict:
    """Perform an operation with comprehensive audit logging.

    Args:
        operation: Name of the operation
        data: Data to process

    Returns:
        dict: Operation result with audit info
    """
    # Create audit entry using runtime dependencies
    audit = await create_comprehensive_audit_log(
        action=f"perform_{operation}", details={"data_length": len(data)}
    )

    # Perform the actual operation
    result = {"operation": operation, "data_processed": len(data), "status": "success"}

    return {
        "result": result,
        "audit": audit,
    }
