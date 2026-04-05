from __future__ import annotations

from typing import Any

from polycode.helpers.models import list_all_models
from polycode.providers.base import BaseProvider


class OpencodeProvider(BaseProvider):
    """
    Provider integration for opencode — an AI coding agent with a headless HTTP server.

    opencode supports 180+ models across 12 providers (ollama, openai, anthropic, google, etc.)
    via its REST API. Sessions are managed in-process by the MCP server.
    """

    def get_name(self) -> str:
        return "opencode"

    def get_install_hint(self) -> str:
        return "npm install -g opencode-ai"

    def check_auth(self, timeout: float = 15.0) -> dict[str, Any]:
        """
        opencode does not have a standalone auth check — auth is per-model-provider.
        Returns a minimal status indicating the binary is present.
        """
        import shutil
        found = shutil.which("opencode") is not None
        return {
            "authenticated": found,
            "method": "per-model-provider",
            "detail": "opencode binary found. Auth is handled per model provider." if found else "opencode not found on PATH.",
            "suggestion": "" if found else self.get_install_hint(),
        }

    def send_prompt(
        self,
        prompt: str,
        model: str | None = None,
        timeout: float = 120.0,
        project_dir: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        opencode prompts are sent via the async HTTP client, not subprocess.
        This method is not used directly — use the handle_* functions in tools.py instead.
        """
        raise NotImplementedError(
            "OpencodeProvider.send_prompt is not used directly. "
            "Use handle_send_message from tools.py with an active session."
        )

    def list_models(self) -> dict[str, Any]:
        """List all models available in opencode across all connected providers."""
        return list_all_models()

    def register(self, mcp: Any, **kwargs: Any) -> None:
        """Register opencode_* tools onto the FastMCP instance."""
        from polycode.providers.opencode.router import register
        register(mcp, **kwargs)
