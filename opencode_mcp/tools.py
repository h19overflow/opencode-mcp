from __future__ import annotations

import logging
import subprocess
from typing import Any

from opencode_mcp.errors import OpencodeValidationError
from opencode_mcp.opencode_client import OpencodeClient
from opencode_mcp.opencode_process import OpencodeProcess
from opencode_mcp.session_manager import SessionManager

logger = logging.getLogger(__name__)


def _validate_model_format(model: str) -> None:
    if "/" not in model or len(model.split("/")) != 2:
        raise OpencodeValidationError(
            message=f"model must be in format 'provider/model', got: '{model}'",
            detail={"provided": model},
            recoverable=True,
            suggestion="Example: 'ollama/qwen3.5:cloud'. Call opencode_list_models to see valid options.",
        )


async def handle_start_session(
    project_dir: str,
    model: str,
    session_manager: SessionManager,
    client: OpencodeClient,
    process: OpencodeProcess,
    default_model: str,
) -> dict[str, Any]:
    _validate_model_format(model)
    opencode_session_id = await client.create_session()
    session_manager.create_session(
        session_id=opencode_session_id,
        model=model,
        project_dir=project_dir,
    )
    logger.info("Started session %s with model %s in %s", opencode_session_id, model, project_dir)
    return {"session_id": opencode_session_id, "model": model, "project_dir": project_dir}


async def handle_send_message(
    session_id: str,
    message: str,
    timeout_seconds: int,
    session_manager: SessionManager,
    client: OpencodeClient,
) -> dict[str, Any]:
    session_manager.get_session(session_id)
    session_manager.add_message(session_id, role="user", content=message)
    result = await client.send_message(session_id=session_id, message=message)
    session_manager.add_message(session_id, role="assistant", content=result["response"])
    session = session_manager.get_session(session_id)
    result["message_index"] = session.message_count - 1
    return result


async def handle_get_history(
    session_id: str,
    session_manager: SessionManager,
) -> dict[str, Any]:
    history = session_manager.get_history(session_id)
    return {"session_id": session_id, "messages": history}


async def handle_list_sessions(session_manager: SessionManager) -> dict[str, Any]:
    return {"sessions": session_manager.list_sessions()}


async def handle_end_session(
    session_id: str,
    session_manager: SessionManager,
) -> dict[str, Any]:
    session_manager.close_session(session_id)
    logger.info("Closed session %s", session_id)
    return {"session_id": session_id, "closed": True}


async def handle_list_models(client: OpencodeClient) -> dict[str, Any]:
    result = subprocess.run(
        ["opencode", "models", "ollama"],
        capture_output=True, text=True, timeout=10,
    )
    models = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {"models": models}


async def handle_set_model(model: str, state: dict[str, Any]) -> dict[str, Any]:
    _validate_model_format(model)
    previous = state["default_model"]
    state["default_model"] = model
    logger.info("Default model changed from %s to %s", previous, model)
    return {"previous_model": previous, "new_model": model}


async def handle_shutdown(
    session_manager: SessionManager,
    process: OpencodeProcess,
) -> dict[str, Any]:
    sessions_closed = session_manager.close_all_sessions()
    await process.stop()
    logger.info("opencode server stopped. %d sessions closed.", sessions_closed)
    return {"stopped": True, "sessions_closed": sessions_closed}
