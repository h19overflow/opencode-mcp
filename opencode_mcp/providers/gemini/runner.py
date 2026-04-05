from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from opencode_mcp.errors import (
    OpencodeBinaryNotFoundError,
    OpencodeProtocolError,
    OpencodeTimeoutError,
    OpencodeValidationError,
)
from opencode_mcp.helpers.cli_runner import (
    _assert_zero_exit,
    _resolve_binary,
    _run_subprocess,
    _extract_gemini_model,
)


def run_prompt(
    prompt: str,
    model: str | None = None,
    timeout: float = 120.0,
    project_dir: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    binary = _resolve_binary("gemini", "npm install -g @google/gemini-cli")
    cmd = [binary, "-p", prompt, "--yolo", "--output-format", "json"]
    if model:
        cmd += ["-m", model]
    if session_id:
        cmd += ["--resume", session_id]

    result = _run_subprocess(cmd, timeout, project_dir, "gemini")
    _assert_zero_exit(result, "gemini", "Run `gemini` interactively to authenticate, or set GEMINI_API_KEY.")

    try:
        data: dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise OpencodeProtocolError(
            message="gemini CLI returned unexpected non-JSON output",
            detail={"raw": result.stdout[:500]},
            recoverable=False,
            suggestion="Ensure gemini CLI >= 0.36.0 and use --output-format json.",
        ) from error

    return {
        "response": data.get("response", ""),
        "model": _extract_gemini_model(data),
        "session_id": data.get("session_id", ""),
    }


def check_auth(timeout: float = 15.0) -> dict[str, Any]:
    binary = _resolve_binary("gemini", "npm install -g @google/gemini-cli")
    result = _run_subprocess(
        [binary, "-p", "hi", "--yolo", "--output-format", "json"],
        timeout, None, "gemini",
    )
    if result.returncode != 0:
        return {
            "authenticated": False,
            "method": "unknown",
            "detail": result.stderr.strip()[:300] or "Non-zero exit.",
            "suggestion": "Set GEMINI_API_KEY env var or run `gemini` interactively to complete OAuth.",
        }
    try:
        data = json.loads(result.stdout)
        return {
            "authenticated": True,
            "method": "api_key_or_oauth",
            "detail": f"OK — model: {_extract_gemini_model(data)}",
            "suggestion": "",
        }
    except (json.JSONDecodeError, KeyError):
        return {
            "authenticated": False,
            "method": "unknown",
            "detail": "Could not parse gemini response.",
            "suggestion": "Set GEMINI_API_KEY or run `gemini` interactively to authenticate.",
        }


def list_sessions(project_dir: str | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    binary = _resolve_binary("gemini", "npm install -g @google/gemini-cli")
    result = _run_subprocess([binary, "--list-sessions"], timeout, project_dir, "gemini")
    sessions = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped:
            sessions.append({"raw": stripped})
    return sessions
