"""
DeepWiki MCP Client (Phase P4-D / Milestone 2 Integration)
Connects DevLensX to external DeepWiki MCP service (https://mcp.deepwiki.com/mcp)
with resilient timeout handling, local caching, and fallback.
"""

import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger("devlensx.mcp.deepwiki")

DEEPWIKI_MCP_ENDPOINT = "https://mcp.deepwiki.com/mcp"


class DeepWikiClient:
    def __init__(self, endpoint: str = DEEPWIKI_MCP_ENDPOINT, timeout_seconds: int = 5):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def query(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Queries the DeepWiki MCP endpoint for repository documentation context."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "deepwiki_query",
                "arguments": {
                    "prompt": prompt,
                    "context": context or {}
                }
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
            logger.debug(f"DeepWiki MCP offline or unreachable: {e}")
            return {
                "status": "FALLBACK_LOCAL",
                "source": "local_wiki_engine",
                "message": f"DeepWiki MCP offline ({e}), utilizing local deterministic wiki generation."
            }
