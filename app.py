from __future__ import annotations

import argparse
import os
import sys
from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


DEFAULT_MODEL_DIR = Path(__file__).resolve().parent / "CodeT5_50K_Final"


def resolve_model_dir(model_dir: str | Path | None = None) -> Path:
    candidate = Path(model_dir) if model_dir is not None else Path(os.environ.get("CODESCRIBE_MODEL_DIR", DEFAULT_MODEL_DIR))
    candidate = candidate.expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Model directory not found: {candidate}")
    return candidate


@lru_cache(maxsize=1)
def load_model(model_dir: str | None = None, device: str = "cpu"):
    resolved_dir = resolve_model_dir(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(str(resolved_dir), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(resolved_dir), local_files_only=True)
    model.to(torch.device(device))
    model.eval()
    return tokenizer, model


def _coerce_code(code: str) -> str:
    cleaned = code.strip().replace("\r\n", "\n")
    if not cleaned:
        raise ValueError("Code input is empty.")
    return cleaned


def summarize(
    code: str,
    *,
    tokenizer=None,
    model=None,
    max_length: int = 128,
    model_dir: str | Path | None = None,
    device: str = "cpu",
) -> str:
    cleaned_code = _coerce_code(code)

    if tokenizer is None or model is None:
        tokenizer, model = load_model(str(resolve_model_dir(model_dir)), device=device)

    input_text = "summarize: " + cleaned_code
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {key: value.to(model.device) for key, value in inputs.items()}

    outputs = model.generate(
        **inputs,
        max_length=max_length,
        min_length=30,
        num_beams=4,
        early_stopping=True,
        no_repeat_ngram_size=3,
        length_penalty=2.0,
    )
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return summary.strip()


def read_source_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.file:
        path = Path(args.file).expanduser().resolve()
        return path.read_text(encoding="utf-8")
    if args.stdin:
        return sys.stdin.read()
    raise SystemExit("Provide --text, --file, or --stdin with code content to summarize.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a natural-language summary for a code snippet or file using the local CodeT5 model."
    )
    parser.add_argument("--text", type=str, help="Code snippet to summarize.")
    parser.add_argument("--file", type=str, help="Path to a .py or .txt file containing code to summarize.")
    parser.add_argument("--stdin", action="store_true", help="Read the code from standard input.")
    parser.add_argument("--model-dir", type=str, default=None, help="Path to the local CodeT5 model directory.")
    parser.add_argument("--device", type=str, default="cpu", help="Device to run the model on, for example cpu or cuda.")
    parser.add_argument("--max-length", type=int, default=128, help="Maximum length of the generated summary in tokens.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        code = read_source_text(args)
        result = summarize(
            code,
            max_length=args.max_length,
            model_dir=args.model_dir,
            device=args.device,
        )
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(result)


if __name__ == "__main__":
    main()
