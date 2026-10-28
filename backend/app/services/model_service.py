from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logger = logging.getLogger("codescribe.model_service")


def find_model_directory(explicit_dir: str | Path | None = None) -> Path:
    """Locate the trained CodeT5 model directory from several plausible locations."""
    if explicit_dir:
        cand = Path(explicit_dir).expanduser().resolve()
        if cand.exists() and is_valid_model_dir(cand):
            return cand

    env_dir = os.getenv("CODESCRIBE_MODEL_DIR")
    if env_dir:
        cand = Path(env_dir).expanduser().resolve()
        if cand.exists() and is_valid_model_dir(cand):
            return cand

    workspace_root = Path(__file__).resolve().parents[3]
    backend_dir = Path(__file__).resolve().parents[2]
    cwd = Path.cwd()

    candidates = [
        workspace_root / "CodeT5_50K_Final",
        workspace_root / "CodeT5-50k_Final",
        workspace_root / "CodeT5-50K_Final",
        backend_dir / "models" / "CodeT5_50K_Final",
        backend_dir / "models" / "CodeT5-50k_Final",
        cwd / "CodeT5_50K_Final",
        cwd / "CodeT5-50k_Final",
    ]

    for candidate in candidates:
        if candidate.exists() and is_valid_model_dir(candidate):
            return candidate.resolve()

    # Search for any directory in workspace matching "codet5" and "50k"
    for parent in [workspace_root, backend_dir, cwd]:
        if parent.exists():
            for item in parent.glob("*[cC]ode[tT]5*"):
                if item.is_dir() and is_valid_model_dir(item):
                    return item.resolve()

    # Fallback to default expected path even if missing yet
    return (workspace_root / "CodeT5_50K_Final").resolve()


def is_valid_model_dir(path: Path) -> bool:
    """Check if the given directory contains required config and model weights."""
    if not path.is_dir():
        return False
    has_config = (path / "config.json").exists()
    has_weights = (path / "model.safetensors").exists() or (path / "pytorch_model.bin").exists()
    return has_config and has_weights


def format_docstring(raw_text: str) -> str:
    """Format raw model output into clean Python docstring."""
    text = raw_text.strip()
    if not text:
        return '"""\n"""'

    # If it already starts and ends with docstring quotes, return as-is
    if (text.startswith('"""') and text.endswith('"""')) or (text.startswith("'''") and text.endswith("'''")):
        return text

    # Strip any accidental single quotes or stray double quotes at boundaries
    stripped = text.strip('"\'')
    return f'"""{stripped}\n"""'


def format_explanation(raw_text: str, code: str) -> str:
    """Format raw model output into a user-friendly code explanation."""
    cleaned = raw_text.strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return "This function executes the logic provided in the input snippet."

    overview = lines[0]
    # Check if there are structured sections (Args/Params, Returns)
    has_sections = any(
        kw in line.lower() for line in lines for kw in ["args:", "returns:", "param", "return:"]
    )

    if not has_sections or len(lines) == 1:
        return overview

    # Build readable formatted explanation
    explanation_parts = [f"**Purpose:** {overview}", "\n**Details:**"]
    for line in lines[1:]:
        explanation_parts.append(f"- {line}")

    return "\n".join(explanation_parts)


class ModelService:
    """Load and run the local CodeT5 model for code docstring and explanation generation."""

    def __init__(self, model_dir: str | Path | None = None):
        self.model_dir: Path = find_model_directory(model_dir)
        self.tokenizer: AutoTokenizer | None = None
        self.model: AutoModelForSeq2SeqLM | None = None
        self.model_loaded: bool = False
        self.last_error: str | None = None
        self.device: str = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name: str = "CodeT5-50K (Fine-Tuned)"

    def validate_model_directory(self) -> None:
        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Model folder not found at: {self.model_dir}. Please ensure CodeT5_50K_Final exists."
            )

        required = [
            "config.json",
            "tokenizer_config.json",
            "tokenizer.json",
        ]
        missing = [name for name in required if not (self.model_dir / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing required tokenizer/config files in {self.model_dir}: {', '.join(missing)}."
            )

        model_files = ["model.safetensors", "pytorch_model.bin"]
        if not any((self.model_dir / name).exists() for name in model_files):
            raise FileNotFoundError(
                f"Missing model weights in {self.model_dir}. Expected one of: {', '.join(model_files)}."
            )

    def load(self) -> bool:
        """Load tokenizer and model onto target device."""
        if self.model_loaded and self.model is not None and self.tokenizer is not None:
            return True

        # Re-check model dir in case it became available
        self.model_dir = find_model_directory(self.model_dir)

        try:
            self.validate_model_directory()
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info("Loading CodeT5 tokenizer from %s", self.model_dir)
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )

            logger.info("Loading CodeT5 model from %s on device: %s", self.model_dir, self.device)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )
            self.model.to(torch.device(self.device))
            self.model.eval()

            self.model_loaded = True
            self.last_error = None
            logger.info("CodeT5-50K loaded successfully on %s!", self.device)
            return True
        except Exception as exc:
            self.model_loaded = False
            self.last_error = str(exc)
            self.model = None
            self.tokenizer = None
            logger.error("Failed to load CodeT5 model: %s", exc)
            return False

    def _generate_raw(self, prompt: str, max_length: int = 128) -> str:
        if self.tokenizer is None or self.model is None:
            raise RuntimeError("Model is not loaded.")

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        input_ids = inputs["input_ids"].to(self.model.device)
        attention_mask = inputs["attention_mask"].to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_length=max_length,
                min_length=15,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3,
                length_penalty=2.0,
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def generate(self, code: str, output_mode: str) -> dict[str, Any]:
        """Generate docstring and/or explanation for the input Python code snippet."""
        if not self.load():
            raise RuntimeError(
                f"Unable to load CodeT5-50K from {self.model_dir}. Error: {self.last_error or 'Folder missing or invalid.'}"
            )

        cleaned_code = code.strip().replace("\r\n", "\n")
        # CodeT5-50k was fine-tuned with task prefix 'summarize: '
        prompt = f"summarize: {cleaned_code}"

        start_time = time.perf_counter()
        raw_output = self._generate_raw(prompt)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        docstring = format_docstring(raw_output) if output_mode in ("docstring", "both") else None
        explanation = format_explanation(raw_output, cleaned_code) if output_mode in ("explain", "both") else None

        return {
            "docstring": docstring,
            "explanation": explanation,
            "raw_summary": raw_output,
            "generation_time_ms": duration_ms,
            "model_name": self.model_name,
            "device": self.device,
        }


model_service = ModelService()
