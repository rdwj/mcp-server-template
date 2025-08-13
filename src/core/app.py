import os
from fastmcp import FastMCP
from .logging import get_logger

APP_NAME = os.getenv("MCP_SERVER_NAME", "fastmcp-unified")
mcp = FastMCP(APP_NAME)
logger = get_logger("server")
