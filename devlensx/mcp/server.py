"""
DevLensX Model Context Protocol (MCP) Server (Phase P4-D)

JSON-RPC 2.0 / Model Context Protocol server exposing repository-grounded tools
for VS Code, JetBrains, and other MCP-compliant IDE extensions.

CRITICAL INVARIANTS:
1. Pure read-only interface to verified snapshot intelligence.
2. Rejects arbitrary filesystem access, commands, or python execution.
3. Errors fail closed with clear status codes.
"""

from __future__ import annotations

import sys
import json
import logging
from typing import Dict, Any, Optional

from devlensx.mcp.tools import MCP_TOOL_DEFINITIONS, MCP_ALL_TOOL_DEFINITIONS, TOOL_HANDLERS
from devlensx.observability.redaction import redact_secret

logger = logging.getLogger("devlensx.mcp")

SERVER_INFO = {
    "name": "devlensx-mcp-server",
    "version": "1.0.0",
}


class MCPServer:
    """Handles JSON-RPC 2.0 protocol requests for DevLensX MCP tools."""

    def __init__(self, include_governance: bool = False):
        self.tools = dict(TOOL_HANDLERS)
        self.tool_definitions = list(MCP_ALL_TOOL_DEFINITIONS if include_governance else MCP_TOOL_DEFINITIONS)

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches a single JSON-RPC 2.0 request."""
        req_id = request_data.get("id")
        method = request_data.get("method")
        params = request_data.get("params") or {}

        if not method:
            return self._error_response(req_id, -32600, "Invalid Request: missing method")

        try:
            if method == "initialize":
                return self._handle_initialize(req_id, params)
            elif method == "notifications/initialized":
                # Client acknowledging initialization
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}
            elif method == "tools/list":
                return self._handle_tools_list(req_id)
            elif method == "tools/call":
                return self._handle_tools_call(req_id, params)
            elif method == "ping":
                return {"jsonrpc": "2.0", "id": req_id, "result": {}}
            else:
                return self._error_response(req_id, -32601, f"Method not found: {method}")
        except Exception as e:
            return self._error_response(req_id, -32603, redact_secret(str(e)))

    def _handle_initialize(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    }
                },
                "serverInfo": SERVER_INFO,
            },
        }

    def _handle_tools_list(self, req_id: Any) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": self.tool_definitions,
            },
        }

    def _handle_tools_call(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}

        if not name or name not in self.tools:
            return self._error_response(req_id, -32602, f"Unknown tool: {name}")

        handler = self.tools[name]
        try:
            result = handler(**arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ],
                    "isError": result.get("status") in ("FAILED", "ERROR", "NOT_FOUND"),
                },
            }
        except (ValueError, PermissionError) as e:
            err_msg = redact_secret(str(e))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"status": "FAILED", "error": err_msg}),
                        }
                    ],
                    "isError": True,
                },
            }
        except TypeError as e:
            return self._error_response(req_id, -32602, f"Invalid arguments for {name}: {str(e)}")

    def _error_response(self, req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": redact_secret(message),
            },
        }

    def run_stdio(self):
        """Standard IO event loop for IDE integration over stdin/stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                response = self.handle_request(data)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError:
                err = self._error_response(None, -32700, "Parse error")
                sys.stdout.write(json.dumps(err) + "\n")
                sys.stdout.flush()
