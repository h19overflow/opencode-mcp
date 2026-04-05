from __future__ import annotations

import json
from typing import Any

from polycode.errors import (
    OpencodeProtocolError,
    OpencodeValidationError,
)
from polycode.helpers.cli_runner import (
    _assert_zero_exit,
    _resolve_binary,
    _run_subprocess,
    _parse_qwen_events,
    _extract_qwen_auth_method,
)


def run_prompt(
    prompt: str,
    model: str | None = None,
    timeout: float = 120.0,
    project_dir: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    binary = _resolve_binary("qwen", "npm install -g @qwen-code/qwen-code")
    cmd = [binary, prompt, "--yolo", "--output-format", "json", "--chat-recording"]
    if model:
        cmd += ["-m", model]
    if session_id:
        cmd += ["--resume", session_id]

    result = _run_subprocess(cmd, timeout, project_dir, "qwen")
    _assert_zero_exit(result, "qwen", "Run `qwen auth qwen-oauth` or `qwen auth coding-plan` to authenticate.")

    try:
        events: list[dict[str, Any]] = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise OpencodeProtocolError(
            message="qwen CLI returned unexpected non-JSON output",
            detail={"raw": result.stdout[:500]},
            recoverable=False,
            suggestion="Ensure qwen CLI >= 0.14.0 and use --output-format json.",
        ) from error

    return _parse_qwen_events(events)


def check_auth(timeout: float = 15.0) -> dict[str, Any]:
    binary = _resolve_binary("qwen", "npm install -g @qwen-code/qwen-code")
    result = _run_subprocess([binary, "auth", "status"], timeout, None, "qwen")
    output = result.stdout.strip() + result.stderr.strip()
    authenticated = result.returncode == 0 and "✓" in output
    return {
        "authenticated": authenticated,
        "method": _extract_qwen_auth_method(output),
        "detail": output[:300],
        "suggestion": "" if authenticated else "Run `qwen auth qwen-oauth` or `qwen auth coding-plan` to authenticate.",
    }
