"""
DeepWiki MCP Client (Milestones 2 & DeepWiki Integration)
Connects DevLensX to external DeepWiki MCP service (https://mcp.deepwiki.com/mcp)
using streamable HTTP MCP wire protocol with resilient error handling and local fallback.
Available Tools:
- read_wiki_structure: Get a list of documentation topics for a GitHub repository
- read_wiki_contents: View documentation about a GitHub repository
- ask_question: Ask any question about a GitHub repository and get an AI-powered, context-grounded response
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

logger = logging.getLogger("devlensx.mcp.deepwiki")

DEEPWIKI_MCP_ENDPOINT = "https://mcp.deepwiki.com/mcp"


class DeepWikiClient:
    def __init__(self, endpoint: str = DEEPWIKI_MCP_ENDPOINT, timeout_seconds: int = 6):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calls an MCP tool over streamable HTTP at https://mcp.deepwiki.com/mcp."""
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
            "Accept": "application/json"
        }
        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("result", {})
        except Exception as e:
            logger.debug(f"DeepWiki MCP tool '{tool_name}' offline or unreachable: {e}")
            return {
                "status": "FALLBACK_LOCAL",
                "source": "local_wiki_engine",
                "message": f"DeepWiki MCP offline ({e}), utilizing local deterministic wiki generation."
            }

    def read_wiki_structure(self, repo_url: str) -> Dict[str, Any]:
        """Tool 1: Get documentation topics/structure for a GitHub repository."""
        return self._call_tool("read_wiki_structure", {"repoUrl": repo_url})

    def read_wiki_contents(self, repo_url: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Tool 2: View documentation contents for a topic or repository."""
        args: Dict[str, Any] = {"repoUrl": repo_url}
        if topic:
            args["topic"] = topic
        return self._call_tool("read_wiki_contents", args)

    def ask_question(self, repo_url: str, question: str) -> Dict[str, Any]:
        """Tool 3: Ask a question about a GitHub repository and get AI-powered grounded response."""
        return self._call_tool("ask_question", {"repoUrl": repo_url, "question": question})

    def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generic query wrapper for backward compatibility."""
        ctx = context or {}
        repo_url = ctx.get("repo_url") or ctx.get("repo") or "https://github.com/prathik-05/DevLensX"
        return self.ask_question(repo_url=repo_url, question=prompt)


DeepWikiMCPClient = DeepWikiClient

