from __future__ import annotations

import logging
from typing import Any

import httpx

from opencode_mcp.errors import OpencodeProtocolError, OpencodeTimeoutError

logger = logging.getLogger(__name__)


class OpencodeClient:
    def __init__(
        self,
        base_url: str,
        request_timeout: float = 120.0,
        auth: tuple[str, str] | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = request_timeout
        self._auth = auth

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
        )

    async def health_check(self) -> bool:
        async with self._make_client() as client:
            response = await client.get("/global/health")
            data = response.json()
            return bool(data.get("healthy", False))

    async def create_session(self, title: str = "") -> str:
        payload: dict[str, Any] = {}
        if title:
            payload["title"] = title
        async with self._make_client() as client:
            response = await client.post("/session", json=payload)
            response.raise_for_status()
            data = response.json()
        if "id" not in data:
            raise OpencodeProtocolError(
                message="opencode /session response missing 'id' field",
                detail={"raw_response": data},
                recoverable=False,
                suggestion="This may indicate an opencode version mismatch. Update opencode.",
            )
        return data["id"]

    async def send_message(
        self,
        session_id: str,
        message: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "parts": [{"type": "text", "text": message}],
        }
        if model:
            payload["model"] = model

        try:
            async with self._make_client() as client:
                response = await client.post(f"/session/{session_id}/message", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise OpencodeTimeoutError(message=f"Request to opencode timed out after {self._timeout}s") from exc

        if "parts" not in data:
            raise OpencodeProtocolError(
                message="opencode message response missing 'parts' field",
                detail={"raw_response": data},
                recoverable=False,
                suggestion="This may indicate an opencode version mismatch. Update opencode.",
            )

        text_parts = [p.get("text", "") for p in data["parts"] if p.get("type") == "text"]
        response_text = "".join(text_parts)

        return {
            "response": response_text,
            "session_id": session_id,
            "partial": False,
        }

    async def list_models(self, provider: str = "ollama") -> list[str]:
        async with self._make_client() as client:
            response = await client.get("/provider")
            response.raise_for_status()
            providers = response.json()

        models = []
        for p in providers:
            if p.get("id") == provider:
                for m in p.get("models", []):
                    model_id = m.get("id", "")
                    if model_id:
                        models.append(f"{provider}/{model_id}")
        return models
