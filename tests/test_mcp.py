"""
Tests for NEVEN MCP (Model Context Protocol) Server — neven/mcp/server.py

Tests cover:
    - Tool definitions structure
    - JSON-RPC protocol handling
    - Initialize handshake
    - Tools list response
    - Tool call routing
    - Claude Desktop config generation
"""

import json
import pytest

from neven.mcp.server import NevenMCPServer, NEVEN_MCP_TOOLS


class TestMCPToolDefinitions:
    """Test that MCP tool definitions are well-formed."""

    def test_tool_count(self):
        """Should expose exactly 4 tools."""
        assert len(NEVEN_MCP_TOOLS) == 4

    def test_tool_names(self):
        """Should expose the correct tool names."""
        names = [t["name"] for t in NEVEN_MCP_TOOLS]
        assert "neven_connect" in names
        assert "neven_perceive" in names
        assert "neven_act" in names
        assert "neven_subscribe" in names

    def test_tool_has_description(self):
        """Each tool should have a non-empty description."""
        for tool in NEVEN_MCP_TOOLS:
            assert "description" in tool
            assert len(tool["description"]) > 10

    def test_tool_has_input_schema(self):
        """Each tool should have a valid input_schema."""
        for tool in NEVEN_MCP_TOOLS:
            assert "input_schema" in tool
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_connect_tool_schema(self):
        """neven_connect should require agent_id and nodes."""
        connect_tool = next(t for t in NEVEN_MCP_TOOLS if t["name"] == "neven_connect")
        schema = connect_tool["input_schema"]
        assert "agent_id" in schema["properties"]
        assert "nodes" in schema["properties"]
        assert "agent_id" in schema["required"]
        assert "nodes" in schema["required"]

    def test_perceive_tool_schema(self):
        """neven_perceive should require node_id."""
        perceive_tool = next(t for t in NEVEN_MCP_TOOLS if t["name"] == "neven_perceive")
        schema = perceive_tool["input_schema"]
        assert "node_id" in schema["properties"]
        assert "node_id" in schema["required"]

    def test_act_tool_schema(self):
        """neven_act should require node_id and action_type."""
        act_tool = next(t for t in NEVEN_MCP_TOOLS if t["name"] == "neven_act")
        schema = act_tool["input_schema"]
        assert "node_id" in schema["properties"]
        assert "action_type" in schema["properties"]
        assert "node_id" in schema["required"]
        assert "action_type" in schema["required"]

    def test_subscribe_tool_schema(self):
        """neven_subscribe should require node_id."""
        subscribe_tool = next(t for t in NEVEN_MCP_TOOLS if t["name"] == "neven_subscribe")
        schema = subscribe_tool["input_schema"]
        assert "node_id" in schema["properties"]
        assert "node_id" in schema["required"]


class TestMCPServerProtocol:
    """Test JSON-RPC 2.0 protocol handling."""

    def setup_method(self):
        """Create a server instance for testing."""
        self.server = NevenMCPServer(
            api_key="test_key",
            base_url="http://localhost:8420",
        )

    def test_handle_initialize(self):
        """Initialize should return protocol version and capabilities."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"},
            },
        }
        response = self.server._handle_request(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        result = response["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "neven-mcp-server"
        assert result["serverInfo"]["version"] == "2.1.0"

    def test_handle_tools_list(self):
        """tools/list should return all tool definitions."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        response = self.server._handle_request(request)
        assert response["id"] == 2
        tools = response["result"]["tools"]
        assert len(tools) == 4

    def test_handle_unknown_method(self):
        """Unknown methods should return error -32601."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "unknown/method",
            "params": {},
        }
        response = self.server._handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_handle_notification(self):
        """Notifications should return None (no response)."""
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        response = self.server._handle_request(request)
        assert response is None

    def test_handle_tools_call_unknown_tool(self):
        """Calling an unknown tool should return an error result."""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        }
        response = self.server._handle_request(request)
        result = response["result"]
        assert result["isError"] is True
        assert "Unknown tool" in result["content"][0]["text"]

    def test_handle_resources_list(self):
        """resources/list should return empty list."""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/list",
            "params": {},
        }
        response = self.server._handle_request(request)
        assert response["result"]["resources"] == []

    def test_handle_prompts_list(self):
        """prompts/list should return empty list."""
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/list",
            "params": {},
        }
        response = self.server._handle_request(request)
        assert response["result"]["prompts"] == []


class TestMCPClaudeDesktopConfig:
    """Test Claude Desktop configuration generation."""

    def test_config_structure(self):
        """Config should have mcpServers.neven with command and args."""
        config = NevenMCPServer.get_claude_desktop_config()
        assert "mcpServers" in config
        assert "neven" in config["mcpServers"]
        neven_config = config["mcpServers"]["neven"]
        assert neven_config["command"] == "neven"
        assert neven_config["args"] == ["mcp-server"]

    def test_config_custom_params(self):
        """Config should use custom API key and base URL."""
        config = NevenMCPServer.get_claude_desktop_config(
            api_key="custom_key",
            base_url="http://custom:9000",
        )
        env = config["mcpServers"]["neven"]["env"]
        assert env["NEVEN_API_KEY"] == "custom_key"
        assert env["NEVEN_BASE_URL"] == "http://custom:9000"


class TestMCPTierRateLimiting:
    """Test that tier rate limiting concepts are in place."""

    def test_server_has_api_key(self):
        """Server should store the API key for rate limiting."""
        server = NevenMCPServer(api_key="nv_live_test")
        assert server.api_key == "nv_live_test"

    def test_server_version(self):
        """Server should report version 2.1.0."""
        server = NevenMCPServer()
        assert server.server_version == "2.1.0"
