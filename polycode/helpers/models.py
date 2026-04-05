from __future__ import annotations

import subprocess
from typing import Any

from polycode.errors import OpencodeValidationError


def list_all_models() -> dict[str, Any]:
    """
    Run `opencode models` and return all available models grouped by provider.

    Only providers that are authenticated and reachable will appear.
    Unauthenticated providers are silently omitted by opencode.

    Returns:
        {
            "models": ["provider/model", ...],   # flat list of all models
            "by_provider": {"provider": [...], ...},  # grouped
            "total": int,
        }
    """
    try:
        result = subprocess.run(
            ["opencode", "models"],
            capture_output=True, text=True, timeout=30,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError as error:
        raise OpencodeValidationError(
            message="opencode binary not found on PATH",
            detail={"binary": "opencode"},
            recoverable=False,
            suggestion="Ensure opencode is installed: npm install -g opencode-ai",
        ) from error
    except subprocess.TimeoutExpired as error:
        raise OpencodeValidationError(
            message="opencode models command timed out after 30 seconds",
            detail={},
            recoverable=True,
            suggestion="Retry or check if opencode is responsive.",
        ) from error

    if result.returncode != 0:
        raise OpencodeValidationError(
            message=f"opencode models command failed with exit code {result.returncode}",
            detail={"stderr": result.stderr},
            recoverable=False,
            suggestion="Check opencode installation or run 'opencode models' manually.",
        )

    grouped: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        model = line.strip()
        if not model:
            continue
        provider = model.split("/")[0] if "/" in model else "other"
        grouped.setdefault(provider, []).append(model)

    all_models = [m for models in grouped.values() for m in models]
    return {"models": all_models, "by_provider": grouped, "total": len(all_models)}
