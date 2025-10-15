"""Enterprise-grade patterns for FastMCP servers.

This module demonstrates how to combine multiple FastMCP Context features
to build production-ready, enterprise-grade MCP tools. It shows best practices
for FIPS-compliant government/enterprise environments.

Enterprise patterns demonstrated:
- Multi-tenant data isolation
- Comprehensive audit logging
- Authentication and authorization
- Progress reporting for long operations
- State management across middleware and tools
- Error handling and validation
- Security best practices

Use this as a reference implementation for building enterprise MCP servers.
"""

import asyncio
from typing import Annotated
from dataclasses import dataclass
from pydantic import Field

from fastmcp import Context
from fastmcp.server.dependencies import get_access_token, get_http_headers
from fastmcp.exceptions import ToolError

from core.logging import get_logger
from core.auth import get_token_scopes

log = get_logger("tools.enterprise")


@dataclass
class AuditRecord:
    """Structured audit record for compliance tracking."""

    action: str
    resource_type: str
    resource_id: str | None
    user_id: str
    tenant_id: str | None
    timestamp: str
    ip_address: str
    status: str
    details: dict


async def create_audit_record(
    ctx: Context,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    status: str = "success",
    details: dict | None = None,
) -> AuditRecord:
    """Create a comprehensive audit record for compliance.

    This utility function demonstrates enterprise audit logging patterns
    by combining multiple Context features.

    Args:
        ctx: FastMCP Context
        action: Action performed (e.g., "create", "read", "update", "delete")
        resource_type: Type of resource (e.g., "document", "user", "config")
        resource_id: Identifier of the specific resource
        status: Operation status (success, failed, denied)
        details: Additional context-specific details

    Returns:
        AuditRecord: Complete audit record for logging/persistence
    """
    # Get user info from token (via runtime dependency or state)
    user_id = ctx.get_state("user_id") or "anonymous"
    tenant_id = ctx.get_state("tenant_id")

    # Get client IP from headers
    headers = get_http_headers()
    ip_address = "unknown"

    # Try to get more accurate IP from X-Forwarded-For header (common in enterprise)
    forwarded_for = headers.get("x-forwarded-for", "")
    if forwarded_for:
        # Take first IP in chain (original client)
        ip_address = forwarded_for.split(",")[0].strip()

    audit = AuditRecord(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        tenant_id=tenant_id,
        timestamp=ctx.get_state("request_timestamp") or "unknown",
        ip_address=ip_address,
        status=status,
        details=details or {},
    )

    # Log the audit record
    await ctx.info(
        f"AUDIT: {user_id}@{tenant_id} {action} {resource_type}:{resource_id} "
        f"from {ip_address} - {status}"
    )

    return audit


async def check_tenant_access(ctx: Context, resource_tenant_id: str) -> bool:
    """Verify user has access to resources in the specified tenant.

    Enterprise multi-tenant pattern: Ensure users can only access data
    from their own tenant.

    Args:
        ctx: FastMCP Context
        resource_tenant_id: Tenant ID of the resource being accessed

    Returns:
        bool: True if access is allowed, False otherwise
    """
    # Get user's tenant from state (set by middleware)
    user_tenant_id = ctx.get_state("tenant_id")

    if not user_tenant_id:
        await ctx.warning("No tenant context found for user")
        return False

    if user_tenant_id != resource_tenant_id:
        await ctx.warning(
            f"Tenant mismatch: user={user_tenant_id}, resource={resource_tenant_id}"
        )
        return False

    return True


async def check_permission(ctx: Context, required_scope: str) -> bool:
    """Check if user has required permission scope.

    Enterprise authorization pattern: Verify fine-grained permissions.

    Args:
        ctx: FastMCP Context
        required_scope: OAuth scope required for the operation

    Returns:
        bool: True if user has the required scope
    """
    # Get scopes from state (set by middleware) or token
    scopes = ctx.get_state("scopes") or get_token_scopes()

    if required_scope in scopes:
        return True

    user_id = ctx.get_state("user_id") or "unknown"
    await ctx.warning(f"Permission denied: {user_id} lacks scope {required_scope}")

    return False


async def fetch_tenant_document(
    document_id: Annotated[str, "Document identifier"],
    ctx: Context = None,
) -> dict:
    """Fetch a document with multi-tenant isolation and audit logging.

    Enterprise pattern demonstrating:
    - Multi-tenant data isolation
    - Permission checking
    - Audit logging
    - Error handling

    Args:
        document_id: ID of the document to fetch
        ctx: FastMCP Context

    Returns:
        dict: Document data if authorized and exists

    Raises:
        ToolError: If unauthorized or document not found
    """
    await ctx.info(f"Fetching document: {document_id}")

    # Check read permission
    if not await check_permission(ctx, "read:documents"):
        _audit = await create_audit_record(
            ctx,
            action="read",
            resource_type="document",
            resource_id=document_id,
            status="denied",
            details={"reason": "insufficient permissions"},
        )
        raise ToolError("Permission denied: requires 'read:documents' scope")

    # Simulate fetching document from database
    # In real implementation, query database with tenant filter
    tenant_id = ctx.get_state("tenant_id")
    mock_document = {
        "id": document_id,
        "tenant_id": tenant_id,
        "title": "Enterprise Document",
        "content": "Confidential content",
        "created_at": "2025-10-15T00:00:00Z",
    }

    # Verify tenant access
    if not await check_tenant_access(ctx, mock_document["tenant_id"]):
        _audit = await create_audit_record(
            ctx,
            action="read",
            resource_type="document",
            resource_id=document_id,
            status="denied",
            details={"reason": "tenant mismatch"},
        )
        raise ToolError("Access denied: document belongs to different tenant")

    # Create success audit record (in real implementation, persist to audit log)
    _audit = await create_audit_record(
        ctx,
        action="read",
        resource_type="document",
        resource_id=document_id,
        status="success",
    )

    await ctx.info(f"Successfully fetched document {document_id}")

    return mock_document


async def bulk_process_documents(
    document_ids: Annotated[list[str], "List of document IDs to process"],
    operation: Annotated[str, "Operation to perform (e.g., 'archive', 'export')"],
    ctx: Context = None,
) -> dict:
    """Process multiple documents with progress reporting and batch audit logging.

    Enterprise pattern demonstrating:
    - Progress reporting for long operations
    - Batch processing with error handling
    - Comprehensive audit logging
    - Transaction-like semantics

    Args:
        document_ids: List of document IDs to process
        operation: Type of operation to perform
        ctx: FastMCP Context

    Returns:
        dict: Processing results with success/failure counts
    """
    await ctx.info(f"Starting bulk {operation} for {len(document_ids)} documents")

    # Check permission
    required_scope = (
        "write:documents" if operation in ["archive", "delete"] else "read:documents"
    )
    if not await check_permission(ctx, required_scope):
        raise ToolError(f"Permission denied: requires '{required_scope}' scope")

    # Initialize tracking
    total = len(document_ids)
    processed = 0
    failed = 0
    results = []

    # Report initial progress
    await ctx.report_progress(progress=0, total=total)

    # Process each document
    for i, doc_id in enumerate(document_ids):
        try:
            # Simulate processing
            await asyncio.sleep(0.1)  # Simulate work

            # Verify tenant access (in real implementation, batch query)
            tenant_id = ctx.get_state("tenant_id")
            doc_tenant = tenant_id  # Mock: would come from database

            if not await check_tenant_access(ctx, doc_tenant):
                raise ToolError(f"Access denied for document {doc_id}")

            # Create audit record for each document (in real implementation, persist to audit log)
            _audit = await create_audit_record(
                ctx,
                action=operation,
                resource_type="document",
                resource_id=doc_id,
                status="success",
            )

            results.append({"document_id": doc_id, "status": "success"})
            processed += 1

        except Exception as e:
            await ctx.warning(f"Failed to process document {doc_id}: {e}")

            # Audit the failure (in real implementation, persist to audit log)
            _audit = await create_audit_record(
                ctx,
                action=operation,
                resource_type="document",
                resource_id=doc_id,
                status="failed",
                details={"error": str(e)},
            )

            results.append({"document_id": doc_id, "status": "failed", "error": str(e)})
            failed += 1

        # Report progress every 10 items or on last item
        if (i + 1) % 10 == 0 or (i + 1) == total:
            await ctx.report_progress(progress=i + 1, total=total)
            percentage = ((i + 1) / total) * 100
            await ctx.info(f"Progress: {i + 1}/{total} ({percentage:.0f}%)")

    # Final progress report
    await ctx.report_progress(progress=total, total=total)

    success_rate = (processed / total * 100) if total > 0 else 0

    summary = {
        "operation": operation,
        "total": total,
        "processed": processed,
        "failed": failed,
        "success_rate": round(success_rate, 2),
        "results": results,
    }

    await ctx.info(
        f"Bulk {operation} complete: {processed} succeeded, {failed} failed "
        f"({success_rate:.1f}% success rate)"
    )

    return summary


async def create_secure_document(
    title: Annotated[
        str, Field(description="Document title", min_length=1, max_length=200)
    ],
    content: Annotated[str, "Document content"],
    classification: Annotated[
        str,
        Field(
            description="Security classification",
            pattern="^(public|internal|confidential|secret)$",
        ),
    ] = "internal",
    ctx: Context = None,
) -> dict:
    """Create a new document with validation and audit logging.

    Enterprise pattern demonstrating:
    - Field validation with Pydantic
    - Security classification
    - Audit logging for data creation
    - Automatic tenant assignment

    Args:
        title: Document title (1-200 characters)
        content: Document content
        classification: Security classification level
        ctx: FastMCP Context

    Returns:
        dict: Created document with metadata

    Raises:
        ToolError: If validation fails or user lacks permission
    """
    await ctx.info(f"Creating document: {title} (classification: {classification})")

    # Check create permission
    if not await check_permission(ctx, "write:documents"):
        _audit = await create_audit_record(
            ctx,
            action="create",
            resource_type="document",
            status="denied",
            details={"title": title, "classification": classification},
        )
        raise ToolError("Permission denied: requires 'write:documents' scope")

    # Additional validation for high-security documents
    if classification in ["confidential", "secret"]:
        if not await check_permission(ctx, "write:classified"):
            raise ToolError(
                f"Permission denied: creating {classification} documents "
                "requires 'write:classified' scope"
            )

    # Get tenant context (automatically assigned to user's tenant)
    tenant_id = ctx.get_state("tenant_id")
    user_id = ctx.get_state("user_id") or "system"

    # Create document (in real implementation, persist to database)
    doc_id = f"doc_{len(title)}_{classification}"  # Mock ID generation
    document = {
        "id": doc_id,
        "title": title,
        "content": content,
        "classification": classification,
        "tenant_id": tenant_id,
        "created_by": user_id,
        "created_at": ctx.get_state("request_timestamp"),
        "status": "active",
    }

    # Create audit record (in real implementation, persist to audit log)
    _audit = await create_audit_record(
        ctx,
        action="create",
        resource_type="document",
        resource_id=doc_id,
        status="success",
        details={
            "title": title,
            "classification": classification,
            "content_length": len(content),
        },
    )

    await ctx.info(f"Document created successfully: {doc_id}")

    return document


async def get_user_activity_summary(ctx: Context = None) -> dict:
    """Get summary of current user's activity and permissions.

    Enterprise pattern demonstrating:
    - User context aggregation
    - Permission listing
    - Session information

    Args:
        ctx: FastMCP Context

    Returns:
        dict: User activity and permission summary
    """
    # Get user context from state
    user_id = ctx.get_state("user_id") or "anonymous"
    tenant_id = ctx.get_state("tenant_id") or "unknown"
    scopes = ctx.get_state("scopes") or []
    role = ctx.get_state("role") or "user"
    organization = ctx.get_state("organization")

    # Get request metadata
    timestamp = ctx.get_state("request_timestamp")

    # Get token info for expiration
    token = get_access_token()
    expires_at = token.expires_at if token else None

    await ctx.info(f"Retrieving activity summary for user: {user_id}")

    summary = {
        "user": {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "organization": organization,
            "role": role,
        },
        "permissions": {
            "scopes": sorted(scopes),
            "can_read": "read:documents" in scopes,
            "can_write": "write:documents" in scopes,
            "can_delete": "delete:documents" in scopes,
            "is_admin": role == "admin",
        },
        "session": {
            "request_timestamp": timestamp,
            "token_expires_at": expires_at,
        },
    }

    return summary
