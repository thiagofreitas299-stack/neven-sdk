"""
NEVEN MCP (Model Context Protocol) Server

Exposes NEVEN as a native tool for AI agents via the Model Context Protocol,
enabling seamless integration with Claude Desktop and other MCP-compatible clients.
"""

from neven.mcp.server import NevenMCPServer

__all__ = ["NevenMCPServer"]
