from __future__ import annotations

from typing import Any

from polycode.providers.base import BaseProvider
from polycode.providers.gemini import runner


class GeminiProvider(BaseProvider):
    """
    Provider integration for the Gemini CLI (google-gemini/gemini-cli).

    Invokes the `gemini` binary as a subprocess in headless mode.
    Sessions are persisted to disk by the Gemini CLI — pass session_id to continue a conversation.

    Model routing:
      gemini-3-flash-preview    DEFAULT  — fast, most tasks
      gemini-3.1-pro-preview    COMPLEX  — deep reasoning, architecture, hard bugs
      gemini-2.5-flash-lite     BULK     — batch/repetitive/loop tasks
    """

    def get_name(self) -> str:
        return "gemini"

    def get_install_hint(self) -> str:
        return "npm install -g @google/gemini-cli"

    def check_auth(self, timeout: float = 15.0) -> dict[str, Any]:
        return runner.check_auth(timeout=timeout)

    def send_prompt(
        self,
        prompt: str,
        model: str | None = None,
        timeout: float = 120.0,
        project_dir: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        return runner.run_prompt(
            prompt=prompt,
            model=model,
            timeout=timeout,
            project_dir=project_dir,
            session_id=session_id,
        )

    def list_models(self) -> dict[str, Any]:
        """Gemini models are determined by the CLI's configured account."""
        return {
            "models": [
                "gemini-3-flash-preview",
                "gemini-3.1-pro-preview",
                "gemini-2.5-flash-lite",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-3.1-flash-lite-preview",
            ],
            "by_provider": {"gemini": [
                "gemini-3-flash-preview",
                "gemini-3.1-pro-preview",
                "gemini-2.5-flash-lite",
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-3.1-flash-lite-preview",
            ]},
            "total": 6,
            "routing": {
                "default": "gemini-3-flash-preview",
                "complex": "gemini-3.1-pro-preview",
                "bulk": "gemini-2.5-flash-lite",
            },
        }

    def list_sessions(self, project_dir: str | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
        return runner.list_sessions(project_dir=project_dir, timeout=timeout)

    def register(self, mcp: Any, **kwargs: Any) -> None:
        from polycode.providers.gemini.router import register
        register(mcp)
