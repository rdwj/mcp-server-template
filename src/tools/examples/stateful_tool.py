"""Stateful tool examples demonstrating Context state management.

These tools show how to access request-scoped state set by middleware,
particularly StateManagementMiddleware for multi-tenant and auth-aware tools.

Key patterns demonstrated:
- Accessing tenant ID for multi-tenant data isolation
- Reading user ID for personalization and audit
- Checking permissions via scopes from state
- Building audit context from multiple state values
"""

from fastmcp import Context

from core.logging import get_logger

log = get_logger("tools.stateful")


async def get_user_context(ctx: Context) -> dict:
    """Get the current user's context from request state.

    This tool demonstrates how to access user/tenant information that was
    extracted from the auth token and stored in Context state by middleware.

    Requires StateManagementMiddleware to be enabled.

    Args:
        ctx: FastMCP Context with state populated by middleware

    Returns:
        dict: User context including user_id, tenant_id, scopes, etc.

    Example:
        # In your MCP server setup:
        from middleware.examples.state_middleware import StateManagementMiddleware
        mcp.add_middleware(StateManagementMiddleware())

        # Register the tool:
        mcp.tool(get_user_context)

        # Tool will return:
        {
            "user_id": "user_123",
            "tenant_id": "tenant_abc",
            "scopes": ["read:data", "write:data"],
            "organization": "acme_corp",
            "role": "admin"
        }
    """
    return {
        "user_id": ctx.get_state("user_id"),
        "tenant_id": ctx.get_state("tenant_id"),
        "scopes": ctx.get_state("scopes") or [],
        "organization": ctx.get_state("organization"),
        "role": ctx.get_state("role"),
        "request_timestamp": ctx.get_state("request_timestamp"),
    }


async def get_tenant_data(resource_type: str, ctx: Context) -> dict:
    """Get tenant-specific data with automatic tenant isolation.

    This tool demonstrates multi-tenant data access where the tenant ID
    is automatically extracted from the auth token via middleware state.

    Args:
        resource_type: Type of resource to fetch (e.g., "customers", "orders")
        ctx: FastMCP Context with tenant_id in state

    Returns:
        dict: Tenant-specific data filtered by tenant ID

    Example:
        # Query returns data for authenticated user's tenant only
        result = await get_tenant_data("customers")
        # Returns: {"tenant_id": "tenant_abc", "data": [...]}
    """
    tenant_id = ctx.get_state("tenant_id")

    if not tenant_id:
        await ctx.warning("No tenant_id in state, returning empty result")
        return {
            "tenant_id": None,
            "resource_type": resource_type,
            "data": [],
            "error": "No tenant context available",
        }

    # In a real implementation, you would query your database
    # filtered by tenant_id to ensure data isolation
    log.info(f"Fetching {resource_type} for tenant {tenant_id}")

    # Simulate tenant-specific data
    mock_data = {
        "customers": [
            {"id": "cust_1", "name": "Customer A", "tenant_id": tenant_id},
            {"id": "cust_2", "name": "Customer B", "tenant_id": tenant_id},
        ],
        "orders": [
            {"id": "ord_1", "amount": 100, "tenant_id": tenant_id},
            {"id": "ord_2", "amount": 250, "tenant_id": tenant_id},
        ],
    }

    return {
        "tenant_id": tenant_id,
        "resource_type": resource_type,
        "data": mock_data.get(resource_type, []),
        "count": len(mock_data.get(resource_type, [])),
    }


async def check_permissions(action: str, ctx: Context) -> dict:
    """Check if the current user has permission for an action.

    Uses scopes from Context state to determine permissions.

    Args:
        action: Action to check (e.g., "read:data", "write:data", "admin")
        ctx: FastMCP Context with scopes in state

    Returns:
        dict: Permission check result with allowed/denied status

    Example:
        result = await check_permissions("write:data")
        # Returns: {"allowed": True, "action": "write:data", "scopes": ["read:data", "write:data"]}
    """
    scopes = ctx.get_state("scopes") or []
    user_id = ctx.get_state("user_id") or "anonymous"
    role = ctx.get_state("role")

    allowed = action in scopes

    # Example: Admin role bypasses specific scope checks
    if role == "admin" and not allowed:
        log.info(f"Admin role {user_id} granted access to {action}")
        allowed = True

    result = {
        "user_id": user_id,
        "action": action,
        "allowed": allowed,
        "scopes": scopes,
        "role": role,
    }

    if allowed:
        log.info(f"Permission granted: {user_id} → {action}")
    else:
        log.warning(f"Permission denied: {user_id} → {action}")

    return result


async def create_audit_record(
    operation: str,
    details: str,
    ctx: Context,
) -> dict:
    """Create an audit record using context state.

    Demonstrates building comprehensive audit logs from middleware state.

    Args:
        operation: Operation being performed (e.g., "data_export", "config_change")
        details: Additional details about the operation
        ctx: FastMCP Context with state populated by middleware

    Returns:
        dict: Audit record with full context

    Example:
        record = await create_audit_record(
            "data_export",
            "Exported customer list to CSV"
        )
        # Returns comprehensive audit record with user, tenant, timestamp, etc.
    """
    # Build audit record from state
    audit_record = {
        "operation": operation,
        "details": details,
        "user_id": ctx.get_state("user_id"),
        "tenant_id": ctx.get_state("tenant_id"),
        "organization": ctx.get_state("organization"),
        "role": ctx.get_state("role"),
        "scopes": ctx.get_state("scopes"),
        "timestamp": ctx.get_state("request_timestamp"),
        "tool_name": ctx.get_state("tool_name"),
    }

    # In a real implementation, you would persist this to an audit log
    log.info(f"AUDIT RECORD: {audit_record}")

    return {
        "status": "recorded",
        "record": audit_record,
    }
