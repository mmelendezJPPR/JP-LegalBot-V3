# Copilot / AI agent quick instructions for JP_IA (JP-LegalBot)

Purpose: give an AI coding agent the minimal, high-value context to be immediately productive in this codebase.

1) Big picture (what this repo is)
- Flask web app: single-process web fronted from `app.py`. This is the main entrypoint and contains routes, DB initialization and orchestration logic.
- AI subsystem: under `ai_system/` with modular pieces:
  - `ai_system/retrieve.py` (HybridRetriever) and `ai_system/answer.py` (AnswerEngine) — core RAG/hybrid logic.
  - `ai_system/prompts.py` — system/user templates used to build prompts.
  - `ai_system/memory.py` — lightweight SQLite-backed conversation memory (token-overlap approach for dev).
  - `ai_system/db.py` — helper functions for FTS/search and DB connections.
- Authentication and core utilities: `core/` contains `auth.py` (SQLite-based auth adapter used by the app).
- Templates & static UI: `templates/` (Jinja2) and `static/` (css, js, images).
- Database files: `database/conversaciones.db`, `database/Usuarios.db`, `database/hybrid_knowledge.db` (init scripts under `scripts/`).

2) Where to start when editing or debugging
- Open `app.py` first — it wires everything: config loading, DB init (`inicializar_base_datos()`), imports of `ai_system` modules and Flask routes.
- Key routes to inspect: `/login` (auth), `/chat` (main chat endpoint), `/test-endpoint` (debug), `/test-auth` (auth check). Search for `@app.route('/login'` to find login logic.
- For RAG/embedding-related work, inspect `ai_system/retrieve.py`, `ai_system/answer.py` and `ai_system/prompts.py` in that order.

3) Developer workflows & commands
- Dev run (fast):
  - Create a `.env` with required keys (see README / DEPLOY_RENDER.md). Minimal: `OPENAI_API_KEY`, `FLASK_ENV=development`, `FLASK_DEBUG=True`.
  - Run locally: `python app.py` (dev server prints detailed logs and tracebacks to the terminal).
- Production-like run (as documented):
  - `gunicorn -c gunicorn_config.py app:app` (README references this for production; use a proper WSGI server).
- DB initialization on a fresh checkout: `python scripts/init_render.py` (creates `database/conversaciones.db` and related tables). For users DB: `python scripts/init_usuarios.py`.

4) Important environment variables & external integrations
- OpenAI / Azure OpenAI: `OPENAI_API_KEY` (or Azure vars like `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`). See `DEPLOY_RENDER.md` for Azure deployment settings.
- Embeddings/FAISS: the project tries to import `faiss` and an embeddings service; if not available it falls back to text-only search (logs: "Sin servicio de embeddings disponible - usando solo búsqueda textual").

5) Project-specific conventions and patterns
- Spanish comments & logging: messages and flash strings are in Spanish — keep translations consistent.
- DB-first, SQLite-centric: app initializes SQLite on startup and stores conversations, metrics and audit tables locally. Prefer using the provided DB helpers in `ai_system/db.py` rather than ad-hoc SQL when possible.
- Minimal memory: `ai_system/memory.py` implements a simple token-overlap memory. It's intentionally simple — treat it as a development helper, not production-grade embeddings.
- Login form fields: `username` and `password` (see `templates/login.html`) — use these exact names when crafting test posts.
- Session usage: Flask `session` stores `user_id`, `username`, `logged_in` and `login_time`. Respect `session.permanent = True` semantics already used.
- Logging: use the existing `logger` patterns in `app.py`. The code logs important debugging info (e.g., `🔍 LOGIN DEBUG`). When adding behavior, follow the same style and include traceable keys.

6) Integration / cross-component notes (where to look for side effects)
- Analytics & learning: `app.log_consulta()` writes to analytics and may call `ai_system.learn.save_learning()` — changes here affect stored learning patterns and database tables (`aprendizaje_sistema`).
- Auth: `core/auth.py` (and a `simple_auth` adapter referenced in change-password flow). Use these for any auth changes instead of replacing logic in `app.py`.
- RAG: `HybridRetriever` will try to use embeddings and FAISS if available but degrades to plain text search — handle both flows when modifying retrieval.
- Templates: Jinja2 templates expect certain variables (e.g., `error` on the login page). When returning templates include those variables to avoid UI errors.

7) Quick examples / troubleshooting patterns
- Reproduce login issues (example):
  1. Start server: `python app.py` (terminal shows tracebacks and detailed login logs).
  2. GET `/login` then POST `username=admin@juntaplanificacion.pr.gov` and `password=admin123` to `/login`.
  3. If you see "Error interno del sistema" in UI, check the server terminal — `app.py` prints `Traceback: ...` with the exception.
- Finding where data is saved: search for `CREATE TABLE` in `scripts/init_render.py` and `inicializar_base_datos()` in `app.py` — those show canonical table names and columns.

8) Files & locations to reference quickly
- Entrypoint: `app.py` (routes, logging, DB init)
- AI logic: `ai_system/answer.py`, `ai_system/retrieve.py`, `ai_system/prompts.py`, `ai_system/memory.py`, `ai_system/db.py`
- Auth: `core/auth.py`
- Init scripts: `scripts/init_render.py`, `scripts/init_usuarios.py`
- Deployment notes: `DEPLOY_RENDER.md`, `README.md`
- Templates: `templates/login.html`, `templates/index.html`, `templates/ChangePassword.html`

9) Constraints & guardrails for AI edits
- Avoid removing or renaming database tables or columns without updating `scripts/init_render.py` and existing queries in `app.py` and `ai_system/*`.
- Keep Spanish logging/messages consistent.
- Preserve `session` keys (`user_id`, `username`, `logged_in`, `auth_method`) to avoid breaking UI and other flows.
- When editing retrieval/embeddings code, implement graceful fallback to text-only search as currently done.

10) If you change behavior, run these smoke checks
- `python scripts/init_render.py` (DB created/updated without errors)
- `python app.py` then visit `/login` and `/test-endpoint` (should return a JSON status)
- POST to `/chat` with a short query to ensure the AI pipeline attaches metadata and logs via `log_consulta()`

If you want, I can now:
- Merge this file into the repo (create `.github/copilot-instructions.md`) — I will commit it for you.
- Expand any section (e.g., give exact function signatures for `HybridRetriever`, examples of `ai_system` return shapes) — tell me which area to deepen.

Please review and tell me which sections you want clarified or extended.