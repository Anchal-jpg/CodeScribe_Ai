# CodeScribe AI 🤖

Intelligent Python docstring and code explanation generator powered by a fine-tuned **CodeT5-50K** neural model (`Salesforce/codet5-small`).

---

## 🚀 Quick Launch

### One-Click Launch (Backend + Frontend)
Double-click `run_all.bat` (or run `./run_all.ps1`).

This automatically starts:
- **FastAPI Backend:** [http://127.0.0.1:8000](http://127.0.0.1:8000) (Interactive Swagger Docs at [/docs](http://127.0.0.1:8000/docs))
- **React Frontend:** [http://localhost:5173](http://localhost:5173)

---

## 🛠 Manual Launch

### 1. Start the Backend
```bash
# Windows Command Prompt or PowerShell:
backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Or run `run_backend.bat`.

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```
Or run `run_frontend.bat`.

---

## 🧠 Model Architecture & Details
- **Trained Model Location:** `CodeT5_50K_Final/`
- **Model Checkpoint:** `Salesforce/codet5-small` fine-tuned on 50,000 code-summary pairs.
- **Inference Task:** Seq2seq code summarization with prefix `summarize: <code snippet>`.
- **Outputs Supported:**
  - **Docstring:** Google/Sphinx format Python docstrings ready to insert into code.
  - **Explanation:** Human-readable explanations describing purpose and key details.
  - **Both:** Delivers both simultaneously.

---

## 📡 REST API Endpoints

- `GET /health` - System health check & model load status.
- `GET /api/model-status` - Detailed model status, compute device, and connection state.
- `POST /api/generate` - Run CodeT5 inference on Python code:
  ```json
  {
    "code": "def calculate_total(items):\n    return sum(items)",
    "output_mode": "both",
    "language": "Python"
  }
  ```

---

## 🧪 Testing

### Run Backend Tests (Pytest)
```bash
backend\.venv\Scripts\python.exe -m pytest backend/tests
```

### Run Frontend Tests (Vitest)
```bash
cd frontend
npm test
```
