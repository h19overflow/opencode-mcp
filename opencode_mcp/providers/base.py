from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """
    Abstract base class for all AI provider integrations.

    Every provider must implement these five capabilities:
      - check_auth      — verify the provider is authenticated and reachable
      - send_prompt     — send a one-shot or continued prompt, return response
      - list_models     — list available models for this provider
      - get_name        — return the provider identifier string
      - get_install_hint — return the install instructions shown in error messages

    Optional overrides:
      - list_sessions   — list persisted sessions (providers that support it)
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the provider's identifier, e.g. 'gemini', 'qwen', 'opencode'."""

    @abstractmethod
    def get_install_hint(self) -> str:
        """Return the install command shown when the provider binary is not found."""

    @abstractmethod
    def check_auth(self, timeout: float = 15.0) -> dict[str, Any]:
        """
        Verify the provider is authenticated and reachable.

        Returns a dict with at minimum:
          authenticated (bool)  — whether the provider is ready to use
          method (str)          — auth method in use (e.g. 'oauth', 'api-key')
          detail (str)          — human-readable status message
          suggestion (str)      — fix instructions when authenticated is False
        """

    @abstractmethod
    def send_prompt(
        self,
        prompt: str,
        model: str | None = None,
        timeout: float = 120.0,
        project_dir: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a prompt to the provider and return the response.

        Returns a dict with at minimum:
          response (str)    — the text response
          model (str)       — model that generated the response
          session_id (str)  — session identifier for continuing the conversation
        """

    @abstractmethod
    def list_models(self) -> dict[str, Any]:
        """
        List all models available from this provider.

        Returns a dict with at minimum:
          models (list[str])           — flat list of all model IDs
          by_provider (dict)           — models grouped by sub-provider (if applicable)
          total (int)                  — total model count
        """

    def list_sessions(self, project_dir: str | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
        """
        List persisted sessions for this provider. Returns an empty list by default.

        Providers that persist sessions to disk should override this method.
        Returns a list of dicts, each with at minimum a 'raw' field describing the session.
        """
        return []

    def register(self, mcp: Any, **kwargs: Any) -> None:
        """
        Register all MCP tools for this provider onto the given FastMCP instance.

        Subclasses must implement this to expose their tools. kwargs allows passing
        server-level shared state (session_manager, process, get_client, etc.).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement register(mcp, **kwargs)"
        )
