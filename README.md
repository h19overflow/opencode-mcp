# polycode

A production-grade MCP (Model Context Protocol) server exposing **15 tools** that let Claude Code (or any MCP client) control three AI coding agents — [opencode](https://opencode.ai), [Gemini CLI](https://github.com/google-gemini/gemini-cli), and [Qwen Code](https://github.com/QwenLM/qwen-code) — with full session continuity, auth checking, and structured error handling.

---

## How It Works

```
Claude Code  (or Gemini CLI / Qwen Code)
    │  calls tools (MCP stdio)
    ▼
polycode server  (this package — auto-started by the MCP client)
    │
    ├── spawns opencode serve  →  talks to any of 182 models via opencode
    ├── invokes gemini CLI     →  Gemini API with session continuity
    └── invokes qwen CLI       →  Qwen API with session continuity
```

The MCP client (Claude Code, Gemini CLI, Qwen Code) auto-starts this server when the session begins. You never start it manually.

---

## Requirements

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **opencode CLI** — for the `opencode_*` tools
   ```bash
   npm install -g opencode-ai
   opencode --version  # should print 1.x.x
   ```

3. **Gemini CLI** — for the `gemini_*` tools _(optional)_
   ```bash
   npm install -g @google/gemini-cli
   gemini --version  # should print 0.36.x or higher
   ```

4. **Qwen Code CLI** — for the `qwen_*` tools _(optional)_
   ```bash
   npm install -g @qwen-code/qwen-code
   qwen --version  # should print 0.14.x or higher
   ```

5. **A model provider for opencode** — for the default `ollama/qwen3.5:cloud`, Ollama must be running locally. See [Changing the Model](#changing-the-opencode-model) for alternatives.

---

## Installation

```bash
pip install polycode
```

Or without installing (requires `uv`):

```bash
uvx polycode
```

---

## MCP Client Setup

All three supported MCP clients use the same config format — only the config file path differs.

**macOS / Linux:**
```json
{
  "mcpServers": {
    "opencode": {
      "command": "polycode",
      "env": {
        "OPENCODE_DEFAULT_MODEL": "ollama/qwen3.5:cloud"
      }
    }
  }
}
```

**Windows** — use the full binary path (find it with `where polycode`):
```json
{
  "mcpServers": {
    "opencode": {
      "command": "C:\\Users\\YourName\\AppData\\Local\\Programs\\Python\\Python313\\Scripts\\polycode.exe",
      "env": {
        "OPENCODE_DEFAULT_MODEL": "ollama/qwen3.5:cloud"
      }
    }
  }
}
```

| MCP Client | Config file |
|------------|-------------|
| **Claude Code** | `~/.claude.json` |
| **Gemini CLI** | `~/.gemini/settings.json` |
| **Qwen Code** | `~/.qwen/settings.json` |

Restart your MCP client after saving. All 15 tools appear automatically.

---

## Tools Reference

### opencode tools (8)

These tools control opencode's headless HTTP server. Sessions are stateful — messages within a session share full context.

---

#### `opencode_start_session`
Start a new opencode session. Must be called before `opencode_send_message`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_dir` | string | No | Absolute path to the project. Defaults to current working directory. |
| `model` | string | No | Model in `provider/model` format. Defaults to `OPENCODE_DEFAULT_MODEL`. |

**Returns:**
```json
{
  "session_id": "ses_2a29...",
  "model": "ollama/qwen3.5:cloud",
  "project_dir": "/path/to/project"
}
```

---

#### `opencode_send_message`
Send a prompt to an active session. Blocks until opencode finishes responding.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | From `opencode_start_session`. |
| `message` | string | Yes | Your prompt. |
| `timeout_seconds` | int | No | Default: `120`. |

**Returns:**
```json
{
  "response": "Here is the updated function...",
  "session_id": "ses_2a29...",
  "message_index": 1,
  "partial": false
}
```

---

#### `opencode_get_history`
Retrieve the full message history for a session (tracked in-process).

| Parameter | Type | Required |
|-----------|------|----------|
| `session_id` | string | Yes |

**Returns:**
```json
{
  "session_id": "ses_2a29...",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "2026-04-05T19:00:00Z"},
    {"role": "assistant", "content": "...", "timestamp": "2026-04-05T19:00:05Z"}
  ]
}
```

---

#### `opencode_list_sessions`
List all active opencode sessions.

**Returns:**
```json
{
  "sessions": [
    {
      "session_id": "ses_2a29...",
      "model": "ollama/qwen3.5:cloud",
      "project_dir": "/path/to/project",
      "message_count": 4,
      "created_at": "2026-04-05T19:00:00Z"
    }
  ]
}
```

---

#### `opencode_end_session`
Close a session and free its resources.

| Parameter | Type | Required |
|-----------|------|----------|
| `session_id` | string | Yes |

**Returns:** `{"session_id": "ses_2a29...", "closed": true}`

---

#### `opencode_list_models`
List all models available in opencode across all authenticated providers, grouped by provider. Only providers you are authenticated/connected to will show models.

**Returns:**
```json
{
  "models": ["ollama/qwen3.5:cloud", "openai/gpt-4o", "google/gemini-2.5-flash", "..."],
  "by_provider": {
    "ollama": ["ollama/qwen3.5:cloud", "..."],
    "openai": ["openai/gpt-4o", "..."],
    "google": ["google/gemini-2.5-flash", "..."]
  },
  "total": 182,
  "default_model": "ollama/qwen3.5:cloud"
}
```

---

#### `opencode_set_model`
Change the default model for new sessions (takes effect immediately for all subsequent `opencode_start_session` calls).

| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `model` | string | Yes | `ollama/qwen3.5:cloud` |

**Returns:** `{"previous_model": "ollama/...", "new_model": "openai/gpt-4o"}`

---

#### `opencode_shutdown`
Gracefully stop the opencode server and close all active sessions.

**Returns:** `{"stopped": true, "sessions_closed": 2}`

---

### Gemini CLI tools (4)

These tools invoke the `gemini` CLI directly. Sessions are persisted to disk by the CLI — pass `session_id` to continue a conversation across calls.

**Requires:** `gemini` CLI installed and authenticated (OAuth or `GEMINI_API_KEY`).

---

#### `gemini_check_auth`
Check whether the Gemini CLI is authenticated before making prompt calls.

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `timeout_seconds` | int | No | `15` |

**Returns:**
```json
{
  "authenticated": true,
  "method": "api_key_or_oauth",
  "detail": "OK — model: gemini-2.5-flash-lite",
  "suggestion": ""
}
```
If `authenticated` is `false`, `suggestion` tells you how to fix it.

---

#### `gemini_prompt`
Send a prompt to Gemini CLI. Returns the response and a `session_id` that can be passed back to continue the conversation.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The prompt to send. |
| `session_id` | string | No | Resume a previous session. Leave empty to start a new one. |
| `model` | string | No | E.g. `gemini-2.5-flash`. Defaults to the CLI's configured model. |
| `timeout_seconds` | int | No | Default: `120`. |
| `project_dir` | string | No | Working directory. Defaults to current directory. |

**Returns:**
```json
{
  "response": "The word you asked me to remember is BLUEBIRD.",
  "model": "gemini-2.5-flash-lite",
  "session_id": "69cfc177-319c-484c-9..."
}
```

**Multi-turn example:**
```
# Turn 1 — new session
gemini_prompt(prompt="Remember the word BLUEBIRD")
→ { session_id: "69cfc177-..." }

# Turn 2 — continue session
gemini_prompt(prompt="What word did I ask you to remember?", session_id="69cfc177-...")
→ { response: "BLUEBIRD" }
```

---

#### `gemini_list_sessions`
List saved Gemini CLI sessions for the current project.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_dir` | string | No | Defaults to current directory. |
| `timeout_seconds` | int | No | Default: `10`. |

**Returns:**
```json
{
  "sessions": [
    {"raw": "0: [2026-04-05] Remember the word BLUEBIRD"},
    {"raw": "1: [2026-04-05] Explain the polycode architecture"}
  ]
}
```

---

### Qwen Code CLI tools (3)

These tools invoke the `qwen` CLI directly. Sessions are persisted to disk by the CLI — pass `session_id` to continue a conversation across calls.

**Requires:** `qwen` CLI installed and authenticated (`qwen auth qwen-oauth` or `qwen auth coding-plan`).

---

#### `qwen_check_auth`
Check whether the Qwen Code CLI is authenticated before making prompt calls.

| Parameter | Type | Required | Default |
|-----------|------|----------|---------|
| `timeout_seconds` | int | No | `15` |

**Returns:**
```json
{
  "authenticated": true,
  "method": "qwen-oauth",
  "detail": "=== Authentication Status ===\n✓ Authentication Method: Qwen OAuth\n  Type: Free tier",
  "suggestion": ""
}
```
If `authenticated` is `false`, `suggestion` tells you the exact command to run.

---

#### `qwen_prompt`
Send a prompt to Qwen Code CLI. Returns the response and a `session_id` that can be passed back to continue the conversation.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The prompt to send. |
| `session_id` | string | No | Resume a previous session. Leave empty to start a new one. |
| `model` | string | No | E.g. `qwen-plus`. Defaults to the CLI's configured model. |
| `timeout_seconds` | int | No | Default: `120`. |
| `project_dir` | string | No | Working directory. Defaults to current directory. |

**Returns:**
```json
{
  "response": "The word you asked me to remember was REDPANDA.",
  "model": "coder-model",
  "session_id": "ead03e7a-afff-4ccd-a..."
}
```

**Multi-turn example:**
```
# Turn 1 — new session
qwen_prompt(prompt="Remember the word REDPANDA")
→ { session_id: "ead03e7a-..." }

# Turn 2 — continue session
qwen_prompt(prompt="What word did I ask you to remember?", session_id="ead03e7a-...")
→ { response: "REDPANDA" }
```

---

## Changing the opencode Model

The model format is `provider/model-name`. Set it via env var:

```json
"env": {
  "OPENCODE_DEFAULT_MODEL": "openai/gpt-4o"
}
```

Or call `opencode_set_model` at runtime. Call `opencode_list_models` to see all 182 available models across your connected providers.

**Common models:**

| Provider | Model string |
|----------|-------------|
| Ollama (local) | `ollama/qwen3.5:cloud` |
| OpenAI | `openai/gpt-4o` |
| Anthropic | `anthropic/claude-sonnet-4-5` |
| Google | `google/gemini-2.5-flash` |
| GitHub Copilot | `github-copilot/claude-sonnet-4.6` |

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_DEFAULT_MODEL` | `ollama/qwen3.5:cloud` | Default model for new opencode sessions |
| `OPENCODE_PORT` | `0` (random) | Port for the opencode server |
| `OPENCODE_STARTUP_TIMEOUT` | `10` | Seconds to wait for opencode to start |
| `OPENCODE_REQUEST_TIMEOUT` | `120` | Seconds before a generation times out |
| `OPENCODE_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `OPENCODE_SERVER_PASSWORD` | _(unset)_ | Optional HTTP Basic Auth password for the opencode server |

---

## Error Handling

Every tool always returns a structured response — never a raw exception:

```json
{
  "error": "OpencodeBinaryNotFoundError",
  "message": "gemini CLI not found on PATH. Install: npm install -g @google/gemini-cli",
  "detail": {},
  "recoverable": false,
  "suggestion": "Install opencode via: npm install -g opencode-ai"
}
```

| Field | Description |
|-------|-------------|
| `error` | Exception class name |
| `message` | What went wrong |
| `detail` | Structured context (stderr, attempted values, etc.) |
| `recoverable` | Whether retrying makes sense |
| `suggestion` | Exact next step to fix it |

**Common errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `OpencodeBinaryNotFoundError` | CLI not on PATH | Install the CLI listed in `suggestion` |
| `OpencodeStartupError` | opencode failed to start | Increase `OPENCODE_STARTUP_TIMEOUT`; check `opencode serve` manually |
| `OpencodeTimeoutError` | Generation took too long | Increase `OPENCODE_REQUEST_TIMEOUT` or simplify the prompt |
| `OpencodeSessionError` | Session ID not found | Call `opencode_list_sessions` to see active sessions |
| `OpencodeValidationError` | Bad input or auth error | Read the `suggestion` field — includes exact CLI auth command if needed |
| `OpencodeProtocolError` | Unexpected CLI output shape | Update the CLI to the latest version |

---

## Troubleshooting

### "polycode not found" on Windows

Use the full path in your MCP config. Find it with:
```powershell
where polycode
```

### opencode server times out on startup

Cloud models do a network handshake on first use. Increase the timeout:
```json
"env": { "OPENCODE_STARTUP_TIMEOUT": "30" }
```

### Tools appear but calls hang

On Windows, subprocesses can inherit a blocked stdin from the MCP stdio pipe. This package sets `stdin=DEVNULL` on all subprocesses — ensure you are on `polycode >= 0.1.0`.

### gemini_prompt or qwen_prompt returns an auth error

Run the auth check first:
- `gemini_check_auth` → reads `suggestion` field for the fix
- `qwen_check_auth` → reads `suggestion` field for the fix

Then authenticate interactively (`gemini` or `qwen auth qwen-oauth`) and retry.

---

## Running Tests

```bash
git clone https://github.com/h19overflow/polycode
cd polycode
pip install -e ".[dev]"

# Unit tests — no CLIs required
pytest tests/ --ignore=tests/test_integration.py -v

# Integration tests — requires opencode + ollama
pytest tests/test_integration.py -m integration -v
```

---

## Contributing

1. Fork the repo
2. `pip install -e ".[dev]"`
3. Write tests first (TDD)
4. `pytest tests/ --ignore=tests/test_integration.py` must pass
5. `pyright .` must show 0 errors
6. Open a PR

---

## License

MIT — see [LICENSE](LICENSE)
