from __future__ import annotations

from typing import Any

from polycode.providers.base import BaseProvider
from polycode.providers.qwen import runner


class QwenProvider(BaseProvider):
    """
    Provider integration for Qwen Code CLI (QwenLM/qwen-code).

    Invokes the `qwen` binary as a subprocess in headless mode.
    Sessions are persisted to disk by the Qwen CLI — pass session_id to continue a conversation.

    Model routing:
      '' (empty)     DEFAULT  — CLI picks best model for auth tier automatically
      qwen-max       COMPLEX  — deep reasoning, architecture, multi-file refactors
      qwen-plus      STANDARD — balanced capability and speed for most coding tasks
      qwen-turbo     BULK     — fastest/cheapest for batch/repetitive/loop tasks
    """

    def get_name(self) -> str:
        return "qwen"

    def get_install_hint(self) -> str:
        return "npm install -g @qwen-code/qwen-code"

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
        """Qwen models available depend on the user's auth tier."""
        return {
            "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
            "by_provider": {"qwen": ["qwen-max", "qwen-plus", "qwen-turbo"]},
            "total": 3,
            "routing": {
                "default": "(empty — CLI picks automatically)",
                "complex": "qwen-max",
                "standard": "qwen-plus",
                "bulk": "qwen-turbo",
            },
        }

    def register(self, mcp: Any, **kwargs: Any) -> None:
        from polycode.providers.qwen.router import register
        register(mcp)
