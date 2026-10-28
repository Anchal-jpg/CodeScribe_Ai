from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.app.schemas import GenerateRequest, GenerateResponse, ModelStatusResponse
    from backend.app.services.mock_service import mock_service
    from backend.app.services.model_service import model_service
except ModuleNotFoundError:
    from app.schemas import GenerateRequest, GenerateResponse, ModelStatusResponse
    from app.services.mock_service import mock_service
    from app.services.model_service import model_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("codescribe.api")

# Default to TRUE so the real CodeT5 model is used automatically
USE_REAL_MODEL = os.getenv("USE_REAL_MODEL", "true").lower() != "false"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager: pre-warm the CodeT5 model on startup."""
    if USE_REAL_MODEL:
        logger.info("Initializing CodeT5-50K model on startup...")
        try:
            success = model_service.load()
            if success:
                logger.info("CodeT5-50K model successfully loaded and ready for queries!")
            else:
                logger.warning("CodeT5 model could not be loaded at startup: %s", model_service.last_error)
        except Exception as exc:
            logger.warning("Exception during model preload: %s", exc)
    yield
    logger.info("Shutting down CodeScribe AI API.")


app = FastAPI(
    title="CodeScribe AI API",
    version="0.2.0",
    description="Code summarization & docstring generation powered by fine-tuned CodeT5-50K",
    lifespan=lifespan,
)

# Allow CORS for development Vite frontend on localhost/127.0.0.1
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict:
    return {
        "app": "CodeScribe AI",
        "version": "0.2.0",
        "mode": "real-model" if USE_REAL_MODEL else "mock",
        "model_loaded": model_service.model_loaded,
        "description": "Understand your code. Generate meaningful docstrings with CodeT5-50K.",
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "real-model" if USE_REAL_MODEL else "mock",
        "model_loaded": model_service.model_loaded,
        "trained_model_connected": model_service.model_loaded,
        "model_dir": str(model_service.model_dir),
        "device": model_service.device,
        "message": (
            "CodeT5 model loaded and ready."
            if model_service.model_loaded
            else "Backend is running (mock or uninitialized mode)."
        ),
    }


@app.get("/api/model-status", response_model=ModelStatusResponse)
def model_status() -> ModelStatusResponse:
    real_mode_enabled = USE_REAL_MODEL
    model_loaded = model_service.load() if real_mode_enabled else False

    if not real_mode_enabled:
        return ModelStatusResponse(
            model_loaded=False,
            mode="mock",
            mock_mode=True,
            trained_model_connected=False,
            message="Mock mode is active (USE_REAL_MODEL=false).",
            model_dir=str(model_service.model_dir),
            device=model_service.device,
        )

    if model_loaded:
        return ModelStatusResponse(
            model_loaded=True,
            mode="real-model",
            mock_mode=False,
            trained_model_connected=True,
            message=f"Real CodeT5-50K model is active and running on {model_service.device.upper()}.",
            model_dir=str(model_service.model_dir),
            device=model_service.device,
        )

    return ModelStatusResponse(
        model_loaded=False,
        mode="real-model",
        mock_mode=False,
        trained_model_connected=False,
        message=f"Model directory found but failed to load: {model_service.last_error}",
        model_dir=str(model_service.model_dir),
        device=model_service.device,
    )


@app.post("/api/generate", response_model=GenerateResponse)
def generate_code(request: GenerateRequest) -> GenerateResponse:
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=400, detail="Code input cannot be empty.")

    if request.output_mode not in {"docstring", "explain", "both"}:
        raise HTTPException(status_code=400, detail="Unsupported output mode.")

    # If mock mode is explicitly forced
    if not USE_REAL_MODEL:
        result = mock_service.generate(request)
        return GenerateResponse(
            mode="mock",
            mock_mode=True,
            model_loaded=False,
            output_mode=request.output_mode,
            docstring=result.get("docstring"),
            explanation=result.get("explanation"),
            status="Mock mode is active. The trained model is bypassed.",
            generation_time_ms=0.0,
            model_name="Mock Generator",
            device="cpu",
        )

    # Real model inference path
    loaded = model_service.load()
    if not loaded:
        logger.warning("Real model load failed (%s); falling back to mock response.", model_service.last_error)
        result = mock_service.generate(request)
        return GenerateResponse(
            mode="mock-fallback",
            mock_mode=True,
            model_loaded=False,
            output_mode=request.output_mode,
            docstring=result.get("docstring"),
            explanation=result.get("explanation"),
            status=f"Fallback active: Could not load trained model ({model_service.last_error}).",
            generation_time_ms=0.0,
            model_name="Mock Fallback",
            device="cpu",
        )

    try:
        result = model_service.generate(request.code, request.output_mode)
        return GenerateResponse(
            mode="real-model",
            mock_mode=False,
            model_loaded=True,
            output_mode=request.output_mode,
            docstring=result.get("docstring"),
            explanation=result.get("explanation"),
            status="Real CodeT5-50K inference completed successfully.",
            generation_time_ms=result.get("generation_time_ms"),
            model_name=result.get("model_name"),
            device=result.get("device"),
        )
    except Exception as exc:
        logger.exception("Inference error: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Inference error with CodeT5 model: {str(exc)}",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
