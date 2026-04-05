from __future__ import annotations

from opencode_mcp.errors import OpencodeValidationError


def validate_model_format(model: str) -> None:
    """Raise OpencodeValidationError if model is not in 'provider/model' format."""
    if "/" not in model or len(model.split("/")) != 2:
        raise OpencodeValidationError(
            message=f"model must be in format 'provider/model', got: '{model}'",
            detail={"provided": model},
            recoverable=True,
            suggestion="Example: 'ollama/qwen3.5:cloud'. Call opencode_list_models to see valid options.",
        )
