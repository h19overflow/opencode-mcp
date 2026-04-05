# tests/test_tools.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from opencode_mcp.tools import (
    handle_start_session,
    handle_send_message,
    handle_get_history,
    handle_list_sessions,
    handle_end_session,
    handle_list_models,
    handle_set_model,
    handle_shutdown,
)
from opencode_mcp.session_manager import SessionManager
from opencode_mcp.errors import OpencodeSessionError, OpencodeValidationError


@pytest.fixture
def session_manager():
    return SessionManager()


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.create_session = AsyncMock(return_value="opencode-sess-1")
    client.send_message = AsyncMock(return_value={"response": "Hello!", "session_id": "sess-1", "partial": False})
    client.list_models = AsyncMock(return_value=["ollama/qwen3.5:cloud"])
    return client


@pytest.fixture
def mock_process():
    proc = AsyncMock()
    proc.is_running = True
    proc.stop = AsyncMock()
    return proc


@pytest.mark.asyncio
async def test_start_session_creates_session(session_manager, mock_client, mock_process):
    result = await handle_start_session(
        project_dir="/tmp",
        model="ollama/qwen3.5:cloud",
        session_manager=session_manager,
        client=mock_client,
        process=mock_process,
        default_model="ollama/qwen3.5:cloud",
    )
    assert result["session_id"] == "opencode-sess-1"
    assert result["model"] == "ollama/qwen3.5:cloud"
    assert result["project_dir"] == "/tmp"


@pytest.mark.asyncio
async def test_send_message_returns_response(session_manager, mock_client, mock_process):
    session_manager.create_session("opencode-sess-1", "ollama/qwen3.5:cloud", "/tmp")
    result = await handle_send_message(
        session_id="opencode-sess-1",
        message="Hello",
        timeout_seconds=30,
        session_manager=session_manager,
        client=mock_client,
    )
    assert result["response"] == "Hello!"
    assert result["partial"] is False


@pytest.mark.asyncio
async def test_send_message_appends_to_history(session_manager, mock_client):
    session_manager.create_session("opencode-sess-1", "ollama/qwen3.5:cloud", "/tmp")
    await handle_send_message(
        session_id="opencode-sess-1",
        message="Hello",
        timeout_seconds=30,
        session_manager=session_manager,
        client=mock_client,
    )
    history = session_manager.get_history("opencode-sess-1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_list_sessions_returns_all(session_manager, mock_client, mock_process):
    session_manager.create_session("s1", "ollama/qwen3.5:cloud", "/tmp")
    session_manager.create_session("s2", "ollama/qwen3.5:cloud", "/tmp")
    result = await handle_list_sessions(session_manager=session_manager)
    ids = [s["session_id"] for s in result["sessions"]]
    assert "s1" in ids
    assert "s2" in ids


@pytest.mark.asyncio
async def test_end_session_closes_it(session_manager, mock_client):
    session_manager.create_session("opencode-sess-1", "ollama/qwen3.5:cloud", "/tmp")
    result = await handle_end_session(session_id="opencode-sess-1", session_manager=session_manager)
    assert result["closed"] is True
    with pytest.raises(OpencodeSessionError):
        session_manager.get_session("opencode-sess-1")


@pytest.mark.asyncio
async def test_set_model_updates_default(mock_process):
    state = {"default_model": "ollama/qwen3.5:cloud"}
    result = await handle_set_model(model="ollama/gemma4:e4b", state=state)
    assert result["previous_model"] == "ollama/qwen3.5:cloud"
    assert result["new_model"] == "ollama/gemma4:e4b"
    assert state["default_model"] == "ollama/gemma4:e4b"


@pytest.mark.asyncio
async def test_set_model_raises_validation_error_on_bad_format():
    state = {"default_model": "ollama/qwen3.5:cloud"}
    with pytest.raises(OpencodeValidationError) as exc_info:
        await handle_set_model(model="badformat", state=state)
    assert "provider/model" in exc_info.value.message


@pytest.mark.asyncio
async def test_shutdown_stops_process_and_closes_sessions(session_manager, mock_process):
    session_manager.create_session("s1", "ollama/qwen3.5:cloud", "/tmp")
    result = await handle_shutdown(session_manager=session_manager, process=mock_process)
    assert result["stopped"] is True
    assert result["sessions_closed"] == 1
    mock_process.stop.assert_called_once()


@pytest.mark.asyncio
async def test_list_models_returns_models_grouped_by_provider(monkeypatch):
    def fake_run(*args, **kwargs):
        class FakeResult:
            returncode = 0
            stdout = "ollama/qwen3.5:cloud\nollama/gemma4:e4b\nopenai/gpt-4o\ngoogle/gemini-2.5-flash\n"
            stderr = ""
        return FakeResult()
    monkeypatch.setattr("opencode_mcp.tools.subprocess.run", fake_run)
    result = await handle_list_models()
    assert "ollama/qwen3.5:cloud" in result["models"]
    assert result["total"] == 4
    assert result["by_provider"]["ollama"] == ["ollama/qwen3.5:cloud", "ollama/gemma4:e4b"]
    assert result["by_provider"]["openai"] == ["openai/gpt-4o"]
    assert result["by_provider"]["google"] == ["google/gemini-2.5-flash"]


@pytest.mark.asyncio
async def test_list_models_returns_empty_when_no_providers_connected(monkeypatch):
    # opencode returns exit 0 with empty stdout when no providers are authenticated
    def fake_run(*args, **kwargs):
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""
        return FakeResult()
    monkeypatch.setattr("opencode_mcp.tools.subprocess.run", fake_run)
    result = await handle_list_models()
    assert result["models"] == []
    assert result["total"] == 0
    assert result["by_provider"] == {}


@pytest.mark.asyncio
async def test_list_models_raises_on_missing_binary(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("opencode not found")
    monkeypatch.setattr("opencode_mcp.tools.subprocess.run", fake_run)
    with pytest.raises(OpencodeValidationError):
        await handle_list_models()


@pytest.mark.asyncio
async def test_list_models_raises_on_nonzero_exit(monkeypatch):
    def fake_run(*args, **kwargs):
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "some error"
        return FakeResult()
    monkeypatch.setattr("opencode_mcp.tools.subprocess.run", fake_run)
    with pytest.raises(OpencodeValidationError):
        await handle_list_models()
