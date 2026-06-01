"""
NEVEN MCP Server — Model Context Protocol Integration

Exposes NEVEN as a native tool for AI agents via the Model Context Protocol (MCP).
Compatible with Claude Desktop and any MCP-compliant client.

Transport: stdio (JSON-RPC 2.0 over stdin/stdout)

Tools exposed:
    - neven_connect: Establish a session with physical infrastructure
    - neven_perceive: Query real-time spatial state of a node
    - neven_act: Execute a safe physical action (DSE-verified)
    - neven_subscribe: Subscribe to real-time spatial events

Usage:
    # Start as standalone server
    from neven.mcp import NevenMCPServer
    server = NevenMCPServer()
    server.run()

    # Or via CLI
    $ neven mcp-server
"""

import json
import sys
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("neven.mcp")


# ─── Tool Definitions ─────────────────────────────────────────────────────────

NEVEN_MCP_TOOLS = [
    {
        "name": "neven_connect",
        "description": (
            "Establish a session with NEVEN physical infrastructure. "
            "Connects an AI agent to physical nodes (cameras, sensors, IoT devices) "
            "and returns a session ID for subsequent operations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "Unique identifier for the AI agent",
                },
                "nodes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of physical node IDs to connect to",
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["perception", "actuation"]},
                    "description": "Required capabilities (perception, actuation)",
                    "default": ["perception"],
                },
            },
            "required": ["agent_id", "nodes"],
        },
    },
    {
        "name": "neven_perceive",
        "description": (
            "Query the real-time spatial state of a physical node. "
            "Returns detected entities, occupancy, semantic description, "
            "and environmental data from cameras and sensors."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The physical node ID to query",
                },
                "query_type": {
                    "type": "string",
                    "enum": ["semantic_state", "entities", "occupancy", "full"],
                    "description": "Type of perception query",
                    "default": "semantic_state",
                },
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "neven_act",
        "description": (
            "Execute a physical action on a node, subject to DSE safety verification. "
            "Actions are cryptographically signed and verified against safety rules "
            "before execution. Examples: unlock doors, adjust lighting, trigger alerts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "Target physical node ID",
                },
                "action_type": {
                    "type": "string",
                    "description": "Type of action to execute (e.g., unlock_compartment, adjust_lighting)",
                },
                "parameters": {
                    "type": "object",
                    "description": "Action-specific parameters",
                    "default": {},
                },
            },
            "required": ["node_id", "action_type"],
        },
    },
    {
        "name": "neven_subscribe",
        "description": (
            "Subscribe to real-time spatial events from a physical node. "
            "Returns recent events and sets up monitoring for the specified event types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The node to subscribe to",
                },
                "event_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "entity_entered",
                            "entity_exited",
                            "occupancy_changed",
                            "anomaly_detected",
                            "safety_violation",
                        ],
                    },
                    "description": "Event types to subscribe to",
                    "default": ["entity_entered", "entity_exited"],
                },
            },
            "required": ["node_id"],
        },
    },
]


# ─── MCP Server ───────────────────────────────────────────────────────────────

class NevenMCPServer:
    """
    Model Context Protocol (MCP) server for NEVEN.

    Implements JSON-RPC 2.0 over stdio transport, exposing NEVEN's core
    operations as tools for AI agents (e.g., Claude Desktop).

    Protocol methods:
        - initialize: Server capability negotiation
        - tools/list: Return available tool definitions
        - tools/call: Execute a tool and return results
        - notifications/initialized: Client ready notification
    """

    def __init__(
        self,
        server_name: str = "neven-mcp-server",
        server_version: str = "2.1.0",
        api_key: str = "",
        base_url: str = "http://localhost:8420",
    ):
        self.server_name = server_name
        self.server_version = server_version
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
        self._initialized = False

    def run(self) -> None:
        """
        Start the MCP server on stdio transport.

        Reads JSON-RPC 2.0 messages from stdin and writes responses to stdout.
        This is the main entry point for Claude Desktop integration.
        """
        logger.info(f"Starting NEVEN MCP Server v{self.server_version}")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON-RPC request
                request = json.loads(line)
                response = self._handle_request(request)

                if response is not None:
                    self._send_response(response)

            except json.JSONDecodeError as e:
                error_response = self._make_error(-32700, f"Parse error: {e}")
                self._send_response(error_response)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"MCP server error: {e}")
                error_response = self._make_error(-32603, f"Internal error: {e}")
                self._send_response(error_response)

    def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route a JSON-RPC request to the appropriate handler."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        # Notifications (no response expected)
        if method == "notifications/initialized":
            self._initialized = True
            return None

        # Methods that require a response
        if method == "initialize":
            result = self._handle_initialize(params)
        elif method == "tools/list":
            result = self._handle_tools_list()
        elif method == "tools/call":
            result = self._handle_tools_call(params)
        elif method == "resources/list":
            result = {"resources": []}
        elif method == "prompts/list":
            result = {"prompts": []}
        else:
            return self._make_error(-32601, f"Method not found: {method}", request_id)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the initialize request — capability negotiation."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {
                "name": self.server_name,
                "version": self.server_version,
            },
        }

    def _handle_tools_list(self) -> Dict[str, Any]:
        """Return the list of available tools."""
        return {"tools": NEVEN_MCP_TOOLS}

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return results."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler_map = {
            "neven_connect": self._tool_connect,
            "neven_perceive": self._tool_perceive,
            "neven_act": self._tool_act,
            "neven_subscribe": self._tool_subscribe,
        }

        handler = handler_map.get(tool_name)
        if not handler:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Unknown tool: {tool_name}",
                    }
                ],
                "isError": True,
            }

        try:
            result = handler(arguments)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2),
                    }
                ],
            }
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {tool_name}: {str(e)}",
                    }
                ],
                "isError": True,
            }

    # ─── Tool Implementations ─────────────────────────────────────────────

    def _get_client(self):
        """Lazily initialize the NEVEN client."""
        if self._client is None:
            from neven.core.client import NevenClient
            self._client = NevenClient(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    def _tool_connect(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute neven_connect tool."""
        client = self._get_client()
        try:
            response = client.connect(
                agent_id=arguments["agent_id"],
                nodes=arguments.get("nodes", []),
                capabilities=arguments.get("capabilities", ["perception"]),
            )
            return {
                "status": "connected",
                "session_id": response.session_id,
                "authorized_nodes": response.authorized_nodes,
                "message": f"Successfully connected as '{arguments['agent_id']}' with access to {len(response.authorized_nodes)} nodes.",
            }
        except ConnectionError:
            return {
                "status": "error",
                "message": "Cannot connect to NEVEN server. Ensure it is running with: neven serve",
            }

    def _tool_perceive(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute neven_perceive tool."""
        client = self._get_client()
        try:
            response = client.perceive(
                node_id=arguments["node_id"],
                query_type=arguments.get("query_type", "semantic_state"),
            )
            result = {
                "node_id": arguments["node_id"],
                "timestamp": response.timestamp.isoformat() if hasattr(response, "timestamp") else None,
            }
            if hasattr(response, "spatial_state") and response.spatial_state:
                ss = response.spatial_state
                result["semantic_description"] = getattr(ss, "semantic_description", "")
                result["occupancy_status"] = getattr(ss, "occupancy_status", "unknown")
                if hasattr(ss, "detected_entities"):
                    result["entities"] = [
                        {
                            "class": getattr(e, "class_label", "unknown"),
                            "confidence": getattr(e, "confidence", 0.0),
                        }
                        for e in (ss.detected_entities or [])
                    ]
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _tool_act(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute neven_act tool."""
        client = self._get_client()
        try:
            response = client.act(
                node_id=arguments["node_id"],
                action_type=arguments["action_type"],
                parameters=arguments.get("parameters", {}),
            )
            return {
                "node_id": arguments["node_id"],
                "action_type": arguments["action_type"],
                "status": response.status,
                "transaction_id": getattr(response, "transaction_id", None),
                "safety_evaluation": getattr(response, "safety_evaluation", None),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _tool_subscribe(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute neven_subscribe tool."""
        client = self._get_client()
        try:
            sub_id = client.subscribe(
                node_id=arguments["node_id"],
                events=arguments.get("event_types", ["entity_entered", "entity_exited"]),
            )
            return {
                "status": "subscribed",
                "subscription_id": sub_id,
                "node_id": arguments["node_id"],
                "event_types": arguments.get("event_types", ["entity_entered", "entity_exited"]),
                "message": f"Subscribed to events on node '{arguments['node_id']}'",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ─── JSON-RPC Helpers ─────────────────────────────────────────────────

    def _send_response(self, response: Dict[str, Any]) -> None:
        """Send a JSON-RPC response to stdout."""
        output = json.dumps(response)
        sys.stdout.write(output + "\n")
        sys.stdout.flush()

    def _make_error(
        self, code: int, message: str, request_id: Any = None
    ) -> Dict[str, Any]:
        """Create a JSON-RPC error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    # ─── Claude Desktop Configuration ─────────────────────────────────────

    @staticmethod
    def get_claude_desktop_config(
        api_key: str = "nv_live_dev",
        base_url: str = "http://localhost:8420",
    ) -> Dict[str, Any]:
        """
        Generate the Claude Desktop configuration for this MCP server.

        Add this to your claude_desktop_config.json:

        Returns:
            Configuration dictionary for Claude Desktop
        """
        return {
            "mcpServers": {
                "neven": {
                    "command": "neven",
                    "args": ["mcp-server"],
                    "env": {
                        "NEVEN_API_KEY": api_key,
                        "NEVEN_BASE_URL": base_url,
                    },
                }
            }
        }


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    """Entry point for the MCP server."""
    import os
    server = NevenMCPServer(
        api_key=os.environ.get("NEVEN_API_KEY", "nv_live_dev"),
        base_url=os.environ.get("NEVEN_BASE_URL", "http://localhost:8420"),
    )
    server.run()


if __name__ == "__main__":
    main()
