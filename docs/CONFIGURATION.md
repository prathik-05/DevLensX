# Configuration
- `OPENAI_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` — LLM available vs deterministic fallback
- `DATABASE_URL` — SQLite
- `JWT_SECRET` — auth
- Ports: backend 8000, frontend 5173 (isolated per E2E test via dynamic ports)
- Kuzu DB: `devlensx_graph_db` or `KUZU_DB_PATH` env for isolated tests
- Limits: MAX_ZIP_SIZE 100MB, MAX_FILES 10k, MAX_SINGLE 10MB, SourceReader 1MB, Deep Research 6/12/20/3
