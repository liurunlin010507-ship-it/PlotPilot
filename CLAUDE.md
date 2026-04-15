# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PlotPilot (墨枢) is an AI-driven long-form novel creation platform. Backend is Python/FastAPI, frontend is Vue 3/TypeScript with Naive UI.

## Commands

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (default port 8005)
uvicorn interfaces.main:app --host 127.0.0.1 --port 8005 --reload

# Run all tests
pytest

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run a single test file
pytest tests/unit/domain/novel/entities/test_chapter.py -v

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Disable autopilot daemon on startup
DISABLE_AUTO_DAEMON=1 uvicorn interfaces.main:app --host 127.0.0.1 --port 8005
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # Dev server on port 3000, proxies /api to backend:8005
npm run build      # vue-tsc type check + vite build
```

### Infrastructure
```bash
docker compose up -d                       # Start Qdrant vector DB (optional)
python scripts/run_migrations.py           # Run DB migrations
python scripts/utils/download_embedding_model.py  # Download BAAI/bge-small-zh-v1.5
```

## Architecture

Domain-Driven Design with four layers. All modules live at repo root (no `src/` directory):

- **`domain/`** — Business entities and domain logic. Submodules: `novel/` (Novel, Chapter, PlotArc, Storyline, Foreshadowing), `bible/` (Character, Location, WorldSetting, RelationshipGraph), `cast/` (character relationships), `knowledge/` (knowledge triples), `shared/` (base classes, exceptions).
- **`application/`** — Use cases, workflows, and application services. Key submodules: `engine/` (chapter generation, autopilot daemon, streaming bus), `analyst/` (voice drift, tension analysis, narrative state machine), `audit/` (chapter review, macro refactoring), `blueprint/` (beat sheets, story structure planning).
- **`infrastructure/`** — External integrations: `ai/` (Anthropic Claude + ByteDance Ark/Doubao providers, vector stores via FAISS/Qdrant), `persistence/` (SQLite repositories, schema migrations, mappers).
- **`interfaces/`** — FastAPI routes organized by module under `api/v1/`: `core/`, `world/`, `engine/`, `audit/`, `analyst/`, `blueprint/`, `workbench/`. Also `api/stats/` for statistics.

### Key Patterns

- **Entrypoint**: `interfaces/main.py` — assembles the FastAPI app, mounts all routers under `/api/v1`, starts the autopilot daemon as a separate multiprocessing.Process.
- **AI provider abstraction**: `infrastructure/ai/` provides LLM clients. Primary: Anthropic Claude. Secondary: ByteDance Ark (Doubao). Local embedding: `sentence-transformers` with `bge-small-zh-v1.5`.
- **Autopilot daemon**: Runs in a background process managed from `interfaces/main.py`. Uses `StreamingBus` (cross-process queue) for SSE to the frontend. Can be disabled with `DISABLE_AUTO_DAEMON=1`.
- **Database**: SQLite via `infrastructure/persistence/`. Schema in `schema.sql`, migrations in `migrations/`. Path configured via `application/paths.py`.
- **Environment**: `.env` file (see `.env.example`) for API keys, model settings, and log config. `HF_HUB_OFFLINE=1` is set at startup to prevent model downloads at runtime.
- **Frontend**: Vue 3 SPA at `frontend/`. Pinia stores for state, axios for API calls. Vite dev server proxies `/api` to backend. `@` alias points to `frontend/src/`.

### Testing

Tests follow the same layer structure under `tests/`: `unit/`, `integration/`, `e2e/`, `manual/`. Pytest config in `pyproject.toml` — markers: `unit`, `integration`, `slow`.

## Configuration

Environment variables (`.env`):
- `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` — Claude API credentials
- `ARK_API_KEY`, `ARK_BASE_URL`, `ARK_MODEL` — ByteDance Doubao credentials
- `LOG_LEVEL`, `LOG_FILE` — Logging
- `CORS_ORIGINS` — Comma-separated allowed origins (defaults to localhost)
- `DISABLE_AUTO_DAEMON` — Set to `1` to skip daemon startup
- `DISABLE_SSL_VERIFY` — Set to `true` to bypass SSL verification
