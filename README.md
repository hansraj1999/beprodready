# Archai

Minimal production-oriented monorepo: **React + TypeScript (Vite)** frontend, **FastAPI** backend, optional **Docker** orchestration.

## Layout

| Path        | Role                                      |
| ----------- | ----------------------------------------- |
| `frontend/` | Vite SPA, nginx image for container runs  |
| `backend/`  | FastAPI app (`uvicorn`), JSON API         |
| `infra/`    | Placeholder for IaC / K8s / prod notes    |

API routes live under **`/api/v1`**.

**Firebase auth:** Send `Authorization: Bearer <Firebase ID token>` for protected routes. The backend verifies the JWT in middleware (for `/api/v1/graphs/*` and `GET /api/v1/users/me`), then `get_current_user` loads or creates a `users` row keyed by Firebase UID.

**AI feature gating:** `free` users are limited to **`FREE_AI_CALLS_MONTHLY_LIMIT`** successful AI operations per **UTC calendar month** (counted in `usage_events` with action `ai.call`). **`pro`** users with a non-expired `valid_till` and **`lifetime`** users are unlimited. Enforced via FastAPI dependency `require_ai_quota` on `POST /evaluate`, `POST /interview/start`, `POST /interview/respond`, `POST /simulate/incident`, and `POST /generate-system`.

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| `POST` | `/api/v1/users` | No | Create a user without Firebase (local / tests) |
| `GET` | `/api/v1/users/me` | Yes | Current user (DB row, auto-provisioned from token) |
| `POST` | `/api/v1/graphs` | Yes | Create a graph for the authenticated user (`name`, `nodes`, `edges`, …) |
| `GET` | `/api/v1/graphs` | Yes | List your graphs (summary: id, name, updated_at) |
| `GET` | `/api/v1/graphs/{id}` | Yes | Fetch your graph (usage logged) |
| `PUT` | `/api/v1/graphs/{id}` | Yes | Update your graph |
| `DELETE` | `/api/v1/graphs/{id}` | Yes | Delete your graph |
| `POST` | `/api/v1/payment/create-order` | Yes | Create a Razorpay order (`{"plan":"pro"|"lifetime"}`); amounts are **server-defined** (paise) |
| `POST` | `/api/v1/payment/webhook` | No (Razorpay HMAC) | Webhook: verifies `X-Razorpay-Signature`, applies `payment.captured` → updates `users.plan` / `valid_till` |
| `POST` | `/api/v1/evaluate` | Yes | System design graph evaluation: rules + LLM → `score`, `strengths`, `weaknesses`, `questions` |
| `POST` | `/api/v1/interview/start` | Yes | Start AI interview; returns `session_id`, opening `message`, `first_question`, `turn` |
| `POST` | `/api/v1/interview/respond` | Yes | Send answer + `session_id`; returns structured evaluation, `follow_up_questions`, `next_question`, `turn` |
| `POST` | `/api/v1/simulate/incident` | Yes | Weak-component scan + LLM (or stub) → `incident`, `impact`, `suggested_fixes` |
| `POST` | `/api/v1/generate-system` | Yes | Text prompt → graph JSON (`nodes`, `edges`) for the canvas; OpenAI when configured, else stub |

Set **`FIREBASE_CREDENTIALS_JSON`** to the full service account JSON string (recommended on Cloud Run / Secret Manager), or **`FIREBASE_CREDENTIALS_PATH`** to a file (local dev). If both are unset, Application Default Credentials are used (e.g. `GOOGLE_APPLICATION_CREDENTIALS` on GCP). See `backend/.env.example`.

**Razorpay:** configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` in `.env`. Point the Razorpay dashboard webhook URL to `https://<host>/api/v1/payment/webhook` and subscribe to **`payment.captured`**. Tune `RAZORPAY_*_AMOUNT_PAISE` and `RAZORPAY_PRO_VALIDITY_DAYS` to match your catalog.

## Prerequisites

- **Local dev:** Node.js 22+, Python 3.12+ (3.12+ recommended; use **SQLAlchemy 2.0.44+** on 3.14), `pip`, **PostgreSQL 16+**
- **Docker:** Docker Engine + Docker Compose v2

## Local development

### One command (Postgres in Docker + API + Vite)

From the **repository root**:

- **Windows:** `.\dev-local.bat` or `.\scripts\dev-local.ps1`
- **macOS / Linux / Git Bash:** `chmod +x scripts/dev-local.sh && ./scripts/dev-local.sh`

This starts `postgres` via Docker Compose, creates `backend/.env` and `frontend/.env` from examples if missing, sets up the Python venv, runs `alembic upgrade head`, opens the API in a **new terminal** (Windows) or background (Unix), then runs `npm run dev`.

- Use **`-SkipPostgres`** on Windows if you already run Postgres locally and `DATABASE_URL` in `backend/.env` points to it.
- On Unix, set **`SKIP_POSTGRES=1`** for the same behavior.

### Database

Run PostgreSQL locally (or use Docker only). Default URL in `backend/.env.example` assumes user/password/db `archai` on `localhost:5432`.

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Unix: cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (OpenAPI) when `ENV` is not `production`.

### Frontend

```bash
cd frontend
copy .env.example .env   # Unix: cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The dev server proxies **`/api`** to `VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8000`).

### Environment files

- `backend/.env.example` — `DATABASE_URL`, CORS, `ENV`, logging, Razorpay, **evaluation** (`EVALUATION_LLM_PROVIDER`, `OPENAI_*`).

**Graph evaluation:** default `EVALUATION_LLM_PROVIDER=stub` needs no API key. For OpenAI, set `EVALUATION_LLM_PROVIDER=openai` and `OPENAI_API_KEY`. Swap-in providers by implementing `LLMProvider` and extending `get_llm_provider()` in `app/evaluation/providers/factory.py`.

**Interview mode** uses the same `EVALUATION_LLM_PROVIDER` / `OPENAI_*` settings and `app/llm/openai_json.py` for chat-style JSON. Conversation state lives in Postgres (`interview_sessions.messages` JSONB). Run `alembic upgrade head` after pulling migration `004_interview`.

**Incident simulation** (`POST /api/v1/simulate/incident`) runs `app/simulation/weak_components.py` (reuses graph rule signals + queue/app/HA heuristics), then either the OpenAI JSON path or a **rule-based stub** scenario (Redis, queue, DB, ingress, or generic app failure) matching the weakest signals.
- `frontend/.env.example` — optional `VITE_API_URL`, proxy target, and **Firebase web config** (`VITE_FIREBASE_*`) for authenticated API calls.

## Docker (full stack)

From the repository root:

```bash
docker compose up --build
```

- **Frontend + API gateway (nginx):** [http://localhost:8080](http://localhost:8080) — static UI and `/api/*` proxied to the backend container.
- **Backend (direct):** [http://localhost:8000](http://localhost:8000)

Compose starts **PostgreSQL**, runs **`alembic upgrade head`** in the backend entrypoint, then serves the API. Set `CORS_ORIGINS` to your real web origin(s) in production and use `ENV=production` to hide OpenAPI UIs.

### Verifying builds (use Docker)

When checking that the stack **builds cleanly** (especially after dependency or TypeScript changes), treat **Docker** as the source of truth:

```bash
docker compose build
# or
docker compose up --build
```

That runs the same **frontend** path as production (`npm ci` when `package-lock.json` exists, then `tsc` + `vite build`) and the **backend** image build on Linux. Local `npm` / `python` on Windows or macOS can differ; **do not rely on host-only `tsc` or `pip` as the final gate**—confirm with Compose builds.

## Scripts (quick reference)

| Location   | Command        | Purpose              |
| ---------- | -------------- | -------------------- |
| `frontend` | `npm run dev`  | Vite dev server      |
| `frontend` | `npm run build`| Typecheck + production bundle |
| `backend`  | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | API with reload |

## License

Add a `LICENSE` file when you publish the project.
