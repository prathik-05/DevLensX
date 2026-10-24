"""
DeepWiki MCP Client (Milestone 2 & DeepWiki MCP Integration)
Connects DevLensX to the external DeepWiki MCP service (https://mcp.deepwiki.com/mcp)
using streamable HTTP MCP wire protocol with support for both application/json
and text/event-stream (SSE), explicit error classification, and local fallback.

Supported DeepWiki Tools:
- read_wiki_structure: Get a list of documentation topics for a GitHub repository
- read_wiki_contents: View documentation contents for a topic or repository
- ask_wiki_question / ask_question: Ask any question about a GitHub repository and get an AI-grounded response
"""

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger("devlensx.mcp.deepwiki")

DEEPWIKI_MCP_ENDPOINT = "https://mcp.deepwiki.com/mcp"
DEFAULT_USER_AGENT = "DevLensX-DeepWiki-MCP/1.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


def _normalize_repo_name(repo_url_or_name: str) -> str:
    """Extracts 'owner/repo' identifier from a URL or raw repository slug."""
    s = (repo_url_or_name or "").strip()
    # Strip git extensions and trailing slashes
    s = re.sub(r"\.git$", "", s).rstrip("/")
    # Extract owner/repo from https://github.com/owner/repo
    m = re.search(r"github\.com[/:]([^/]+/[^/]+)$", s)
    if m:
        return m.group(1)
    parts = s.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return s


class DeepWikiClient:
    """Standards-compliant Streamable HTTP MCP client for DeepWiki."""

    def __init__(self, endpoint: str = DEEPWIKI_MCP_ENDPOINT, timeout_seconds: int = 8):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calls an MCP tool over streamable HTTP at https://mcp.deepwiki.com/mcp.
        Handles both application/json and text/event-stream (SSE) response modes."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 1
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": DEFAULT_USER_AGENT,
            "Mcp-Version": MCP_PROTOCOL_VERSION
        }

        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw_bytes = resp.read()

                # Case 1: Streamable HTTP SSE response (text/event-stream)
                if "text/event-stream" in content_type:
                    return self._parse_sse_response(raw_bytes.decode("utf-8", errors="replace"), tool_name)

                # Case 2: Standard JSON response (application/json)
                try:
                    data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
                    if "error" in data:
                        return {
                            "status": "TOOL_ERROR",
                            "remote_mcp_available": True,
                            "tool": tool_name,
                            "error": data["error"].get("message", str(data["error"])),
                            "source": "remote_deepwiki_mcp"
                        }
                    result = data.get("result", {})
                    return {
                        "status": "SUCCESS",
                        "remote_mcp_available": True,
                        "tool": tool_name,
                        "result": result,
                        "source": "remote_deepwiki_mcp"
                    }
                except json.JSONDecodeError as jde:
                    return {
                        "status": "PROTOCOL_ERROR",
                        "remote_mcp_available": True,
                        "tool": tool_name,
                        "error": f"Invalid JSON response: {jde}",
                        "source": "remote_deepwiki_mcp"
                    }

        except urllib.error.HTTPError as he:
            logger.debug("DeepWiki MCP HTTP error %s: %s", he.code, he.reason)
            return {
                "status": "TOOL_ERROR" if he.code in (400, 422) else "FALLBACK_LOCAL",
                "remote_mcp_available": he.code in (400, 422),
                "tool": tool_name,
                "error": f"HTTP {he.code}: {he.reason}",
                "source": "local_wiki_engine",
                "message": f"DeepWiki MCP returned HTTP {he.code}, using local deterministic wiki."
            }
        except Exception as e:
            logger.debug("DeepWiki MCP transport offline or unreachable: %s", e)
            return {
                "status": "FALLBACK_LOCAL",
                "remote_mcp_available": False,
                "tool": tool_name,
                "source": "local_wiki_engine",
                "message": f"DeepWiki MCP offline ({e}), utilizing local deterministic wiki generation."
            }

    def _parse_sse_response(self, text: str, tool_name: str) -> Dict[str, Any]:
        """Parses Server-Sent Events (SSE) stream into JSON-RPC result or error."""
        last_data = None
        for line in text.splitlines():
            line_str = line.strip()
            if line_str.startswith("data: "):
                try:
                    last_data = json.loads(line_str[6:])
                except Exception:
                    pass

        if not last_data:
            return {
                "status": "PROTOCOL_ERROR",
                "remote_mcp_available": True,
                "tool": tool_name,
                "error": "Empty or unparseable SSE event stream from MCP server",
                "source": "remote_deepwiki_mcp"
            }

        if "error" in last_data:
            return {
                "status": "TOOL_ERROR",
                "remote_mcp_available": True,
                "tool": tool_name,
                "error": last_data["error"].get("message", str(last_data["error"])),
                "source": "remote_deepwiki_mcp"
            }

        res = last_data.get("result", {})
        if res.get("isError"):
            err_msg = ""
            for item in res.get("content", []):
                if item.get("type") == "text":
                    err_msg += item.get("text", "")
            return {
                "status": "TOOL_ERROR",
                "remote_mcp_available": True,
                "tool": tool_name,
                "error": err_msg or "Tool reported an internal error",
                "source": "remote_deepwiki_mcp"
            }

        return {
            "status": "SUCCESS",
            "remote_mcp_available": True,
            "tool": tool_name,
            "result": res,
            "source": "remote_deepwiki_mcp"
        }

    def read_wiki_structure(self, repo_url_or_name: str) -> Dict[str, Any]:
        """Tool 1: Get documentation topics/structure for a GitHub repository."""
        repo_name = _normalize_repo_name(repo_url_or_name)
        return self._call_tool("read_wiki_structure", {"repoName": repo_name})

    def read_wiki_contents(self, repo_url_or_name: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Tool 2: View documentation contents for a topic or repository."""
        repo_name = _normalize_repo_name(repo_url_or_name)
        args: Dict[str, Any] = {"repoName": repo_name}
        if topic:
            args["topic"] = topic
        return self._call_tool("read_wiki_contents", args)

    def ask_question(self, repo_url_or_name: str, question: str) -> Dict[str, Any]:
        """Tool 3: Ask a question about a GitHub repository and get AI-powered grounded response."""
        repo_name = _normalize_repo_name(repo_url_or_name)
        # DeepWiki MCP server registers this tool as 'ask_wiki_question' (with 'ask_question' alias)
        res = self._call_tool("ask_wiki_question", {"repoName": repo_name, "question": question})
        if res.get("status") == "TOOL_ERROR" and "not found" in str(res.get("error", "")).lower():
            res = self._call_tool("ask_question", {"repoName": repo_name, "question": question})
        return res

    def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generic query wrapper for backward compatibility."""
        ctx = context or {}
        repo_url = ctx.get("repo_url") or ctx.get("repo") or "mermaid-js/mermaid"
        return self.ask_question(repo_url_or_name=repo_url, question=prompt)


DeepWikiMCPClient = DeepWikiClient
