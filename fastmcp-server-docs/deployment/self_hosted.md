# Self-Hosted Remote MCP

> Deploy your FastMCP server as a remote MCP service accessible via URL

<Tip>
  STDIO transport is perfect for local development and desktop applications. But to unlock the full potential of MCP—centralized services, multi-client access, and network availability—you need remote HTTP deployment.
</Tip>

This guide walks you through deploying your FastMCP server as a remote MCP service that's accessible via a URL. Once deployed, your MCP server will be available over the network, allowing multiple clients to connect simultaneously and enabling integration with cloud-based LLM applications. This guide focuses specifically on remote MCP deployment, not local STDIO servers.

## Choosing Your Approach

FastMCP provides two ways to deploy your server as an HTTP service. Understanding the trade-offs helps you choose the right approach for your needs.

The **direct HTTP server** approach is simpler and perfect for getting started quickly. You modify your server's `run()` method to use HTTP transport, and FastMCP handles all the web server configuration. This approach works well for standalone deployments where you want your MCP server to be the only service running on a port.

The **ASGI application** approach gives you more control and flexibility. Instead of running the server directly, you create an ASGI application that can be served by production-grade servers like Uvicorn or Gunicorn. This approach is better when you need advanced server features like multiple workers, custom middleware, or when you're integrating with existing web applications.

### Direct HTTP Server

The simplest way to get your MCP server online is to use the built-in `run()` method with HTTP transport. This approach handles all the server configuration for you and is ideal when you want a standalone MCP server without additional complexity.

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool
def process_data(input: str) -> str:
    """Process data on the server"""
    return f"Processed: {input}"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

Run your server with a simple Python command:

```bash
python server.py
```

Your server is now accessible at `http://localhost:8000/mcp/` (or use your server's actual IP address for remote access).

This approach is ideal when you want to get online quickly with minimal configuration. It's perfect for internal tools, development environments, or simple deployments where you don't need advanced server features. The built-in server handles all the HTTP details, letting you focus on your MCP implementation.

### ASGI Application

For production deployments, you'll often want more control over how your server runs. FastMCP can create a standard ASGI application that works with any ASGI server like Uvicorn, Gunicorn, or Hypercorn. This approach is particularly useful when you need to configure advanced server options, run multiple workers, or integrate with existing infrastructure.

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool
def process_data(input: str) -> str:
    """Process data on the server"""
    return f"Processed: {input}"

# Create ASGI application
app = mcp.http_app()
```

Run with any ASGI server - here's an example with Uvicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Your server is accessible at the same URL: `http://localhost:8000/mcp/` (or use your server's actual IP address for remote access).

The ASGI approach shines in production environments where you need reliability and performance. You can run multiple worker processes to handle concurrent requests, add custom middleware for logging or monitoring, integrate with existing deployment pipelines, or mount your MCP server as part of a larger application. This flexibility makes it the preferred choice for serious deployments.

## Configuring Your Server

### Custom Path

By default, your MCP server is accessible at `/mcp/` on your domain. You can customize this path to fit your URL structure or avoid conflicts with existing endpoints. This is particularly useful when integrating MCP into an existing application or following specific API conventions.

```python
# Option 1: With mcp.run()
mcp.run(transport="http", host="0.0.0.0", port=8000, path="/api/mcp/")

# Option 2: With ASGI app
app = mcp.http_app(path="/api/mcp/")
```

Now your server is accessible at `http://localhost:8000/api/mcp/`.

### Authentication

<Warning>
  Authentication is **highly recommended** for remote MCP servers. Some LLM clients require authentication for remote servers and will refuse to connect without it.
</Warning>

FastMCP supports multiple authentication methods to secure your remote server. See the [Authentication Overview](/servers/auth/authentication) for complete configuration options including Bearer tokens, JWT, and OAuth.

### Health Checks

Health check endpoints are essential for monitoring your deployed server and ensuring it's responding correctly. FastMCP allows you to add custom routes alongside your MCP endpoints, making it easy to implement health checks that work with both deployment approaches.

```python
from starlette.responses import JSONResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})
```

This health endpoint will be available at `http://localhost:8000/health` and can be used by load balancers, monitoring systems, or deployment platforms to verify your server is running.

## Integration with Web Frameworks

If you already have a web application running, you can add MCP capabilities by mounting a FastMCP server as a sub-application. This allows you to expose MCP tools alongside your existing API endpoints, sharing the same domain and infrastructure. The MCP server becomes just another route in your application, making it easy to manage and deploy.

For detailed integration guides, see:

* [FastAPI Integration](/integrations/fastapi)
* [ASGI / Starlette Integration](/integrations/asgi)

Here's a quick example showing how to add MCP to an existing FastAPI application:

```python
from fastapi import FastAPI
from fastmcp import FastMCP

# Your existing API
api = FastAPI()

@api.get("/api/status")
def status():
    return {"status": "ok"}

# Create your MCP server
mcp = FastMCP("API Tools")

@mcp.tool
def query_database(query: str) -> dict:
    """Run a database query"""
    return {"result": "data"}

# Mount MCP at /mcp
api.mount("/mcp", mcp.http_app())

# Run with: uvicorn app:api --host 0.0.0.0 --port 8000
```

Your existing API remains at `http://localhost:8000/api/` while MCP is available at `http://localhost:8000/mcp/`.

## Production Deployment

### Running with Uvicorn

When deploying to production, you'll want to optimize your server for performance and reliability. Uvicorn provides several options to improve your server's capabilities, including running multiple worker processes to handle concurrent requests and enabling enhanced logging for monitoring.

```bash
# Install uvicorn with standard extras for better performance
pip install 'uvicorn[standard]'

# Run with multiple workers for better concurrency
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4

# Enable detailed logging for monitoring
uvicorn app:app --host 0.0.0.0 --port 8000 --log-level info
```

### Environment Variables

Production deployments should never hardcode sensitive information like API keys or authentication tokens. Instead, use environment variables to configure your server at runtime. This keeps your code secure and makes it easy to deploy the same code to different environments with different configurations.

Here's an example using bearer token authentication (though OAuth is recommended for production):

```python
import os
from fastmcp import FastMCP
from fastmcp.server.auth import BearerTokenAuth

# Read configuration from environment
auth_token = os.environ.get("MCP_AUTH_TOKEN")
if auth_token:
    auth = BearerTokenAuth(token=auth_token)
    mcp = FastMCP("Production Server", auth=auth)
else:
    mcp = FastMCP("Production Server")

app = mcp.http_app()
```

Deploy with your secrets safely stored in environment variables:

```bash
MCP_AUTH_TOKEN=secret uvicorn app:app --host 0.0.0.0 --port 8000
```

## Testing Your Deployment

Once your server is deployed, you'll need to verify it's accessible and functioning correctly. For comprehensive testing strategies including connectivity tests, client testing, and authentication testing, see the [Testing Your Server](/development/tests) guide.

## Hosting Your Server

This guide has shown you how to create an HTTP-accessible MCP server, but you'll still need a hosting provider to make it available on the internet. Your FastMCP server can run anywhere that supports Python web applications:

* **Cloud VMs** (AWS EC2, Google Compute Engine, Azure VMs)
* **Container platforms** (Cloud Run, Container Instances, ECS)
* **Platform-as-a-Service** (Railway, Render, Vercel)
* **Edge platforms** (Cloudflare Workers)
* **Kubernetes clusters** (self-managed or managed)

The key requirements are Python 3.10+ support and the ability to expose an HTTP port. Most providers will require you to package your server (requirements.txt, Dockerfile, etc.) according to their deployment format. For managed, zero-configuration deployment, see [FastMCP Cloud](/deployment/fastmcp-cloud).
