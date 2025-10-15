"""State management middleware example for FastMCP v2.11.0+.

This middleware demonstrates how to use Context state management to pass
data from middleware to tools. This is particularly useful for:
- Multi-tenant applications (tenant ID from auth → tools)
- Request-scoped authentication context
- Audit logging (user ID, timestamp → tools)
- Feature flags or permissions

Example use cases:
    - Extract tenant ID from JWT and make it available to all tools
    - Set request timestamp for consistent audit logging
    - Pass user permissions to tools without re-parsing tokens
"""

from datetime import datetime

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
import mcp.types as mt
from fastmcp.tools.tool import ToolResult
from fastmcp.server.dependencies import get_access_token

from core.logging import get_logger

log = get_logger("middleware.state")


class StateManagementMiddleware(Middleware):
    """Middleware that extracts auth info and stores it in request-scoped state.

    This middleware:
    1. Extracts user/tenant info from the access token
    2. Stores it in Context state for tools to access
    3. Adds request metadata (timestamp, request ID)

    Tools can then access this state using `ctx.get_state(key)`.

    Example:
        from middleware.examples.state_middleware import StateManagementMiddleware

        mcp.add_middleware(StateManagementMiddleware())

        @mcp.tool
        async def get_data(ctx: Context) -> dict:
            tenant_id = ctx.get_state("tenant_id")
            user_id = ctx.get_state("user_id")
            return {"tenant": tenant_id, "user": user_id}
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Extract auth info and store in context state before tool execution.

        Args:
            context: Middleware context with request parameters
            call_next: Next handler in the middleware chain

        Returns:
            Tool execution result
        """
        tool_name = context.message.name

        # Set request metadata in state
        context.fastmcp_context.set_state(
            "request_timestamp", datetime.utcnow().isoformat()
        )
        context.fastmcp_context.set_state("tool_name", tool_name)

        # Extract auth info from token and store in state
        try:
            token = get_access_token()
            if token and token.claims:
                # Standard JWT claims
                user_id = token.claims.get("sub")  # Subject (user ID)
                if user_id:
                    context.fastmcp_context.set_state("user_id", user_id)
                    log.debug(f"Set user_id in state: {user_id}")

                # Custom claims for multi-tenancy
                tenant_id = token.claims.get("tenant_id")
                if tenant_id:
                    context.fastmcp_context.set_state("tenant_id", tenant_id)
                    log.debug(f"Set tenant_id in state: {tenant_id}")

                # Store permissions/scopes for easy access
                scopes = token.claims.get("scopes", [])
                scope_str = token.claims.get("scope", "")
                all_scopes = (
                    set(scopes) | set(scope_str.split()) if scope_str else set(scopes)
                )
                if all_scopes:
                    context.fastmcp_context.set_state("scopes", list(all_scopes))
                    log.debug(f"Set scopes in state: {all_scopes}")

                # Store organization/role if present
                organization = token.claims.get("org") or token.claims.get(
                    "organization"
                )
                if organization:
                    context.fastmcp_context.set_state("organization", organization)

                role = token.claims.get("role")
                if role:
                    context.fastmcp_context.set_state("role", role)

                log.info(
                    f"State set for {tool_name}: user={user_id}, tenant={tenant_id}"
                )
            else:
                log.debug(
                    f"No token found for {tool_name}, state not populated with auth info"
                )

        except Exception as e:
            log.warning(f"Failed to extract auth info for state: {e}")
            # Continue execution even if we can't extract auth info

        # Execute the tool (which can now access state via ctx.get_state())
        return await call_next(context)


class AuditLoggingMiddleware(Middleware):
    """Middleware that uses state for audit logging.

    This middleware reads state set by StateManagementMiddleware and
    logs comprehensive audit information for compliance.

    Example:
        # Add both middleware in order
        mcp.add_middleware(StateManagementMiddleware())
        mcp.add_middleware(AuditLoggingMiddleware())
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Log audit information before and after tool execution.

        Args:
            context: Middleware context with request parameters
            call_next: Next handler in the middleware chain

        Returns:
            Tool execution result
        """
        # Read state set by StateManagementMiddleware
        user_id = context.fastmcp_context.get_state("user_id") or "anonymous"
        tenant_id = context.fastmcp_context.get_state("tenant_id") or "unknown"
        timestamp = context.fastmcp_context.get_state("request_timestamp")
        tool_name = context.message.name

        # Log before execution
        log.info(
            f"AUDIT: user={user_id} tenant={tenant_id} tool={tool_name} "
            f"timestamp={timestamp} status=started"
        )

        try:
            # Execute tool
            result = await call_next(context)

            # Log success
            log.info(
                f"AUDIT: user={user_id} tenant={tenant_id} tool={tool_name} "
                f"timestamp={timestamp} status=completed"
            )

            return result

        except Exception as e:
            # Log failure
            log.error(
                f"AUDIT: user={user_id} tenant={tenant_id} tool={tool_name} "
                f"timestamp={timestamp} status=failed error={str(e)}"
            )
            raise
