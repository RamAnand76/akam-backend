# Akam Backend API

Production-ready FastAPI backend for the **Akam** companion app, built to strict FAANG-grade security standards according to [akam_api_contract.md](akam_api_contract.md).

## Features
- **FastAPI 0.115+**: Modern typed path operations, `Annotated` dependencies, strict Pydantic v2 schemas.
- **Strict Response Envelopes**: Uniform `ApiResponse[T]` across all endpoints and errors.
- **Authentication**: RS256 2048-bit JWT with refresh token rotation and instant revocation blacklisting.
- **Database**: Async SQLAlchemy 2.0 with SQLite (`sqlite+aiosqlite`) local engine (fully portable to PostgreSQL + pgvector).
- **AI Integration**: Gemma model family integration for intent detection, entity extraction, and conversational responses.
- **Security**: Prompt injection scanning, null-byte stripping, 24-hour request idempotency, constant-time anti-timing checks (50ms min) for IDOR protection, and strict security headers.

## Getting Started

### 1. Requirements
- Python 3.11+
- `uv` (recommended)

### 2. Setup Environment & Install Dependencies
```bash
uv sync
uv pip install pytest pytest-asyncio pytest-cov
```

### 3. Run Development Server
```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
Open interactive API docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Run Automated Tests
```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v
```
