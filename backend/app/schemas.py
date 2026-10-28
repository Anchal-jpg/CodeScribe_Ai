from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Python source code to analyze")
    output_mode: Literal["docstring", "explain", "both"] = Field(
        default="both",
        description="Type of output to generate",
    )
    language: str = Field(default="Python", description="Programming language")

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Code input cannot be empty.")
        return stripped


class GenerateResponse(BaseModel):
    mode: str
    mock_mode: bool
    model_loaded: bool
    output_mode: Literal["docstring", "explain", "both"]
    docstring: str | None = None
    explanation: str | None = None
    status: str
    generation_time_ms: float | None = None
    model_name: str | None = None
    device: str | None = None


class ModelStatusResponse(BaseModel):
    model_loaded: bool
    mode: str
    mock_mode: bool
    trained_model_connected: bool
    message: str
    model_dir: str | None = None
    device: str | None = None

