# DevOps & Setup Guide — Hisaab

> **Audience:** Dev 1 (frontend), Dev 2 (backend), and any future contributor.  
> This document covers the full monorepo layout, local environment setup, branching strategy, command references, deployment notes, testing strategy, and optional Docker Compose configuration.

---

## Table of Contents

1. [Monorepo Directory Tree](#1-monorepo-directory-tree)
2. [Environment Variables (.env.example)](#2-environment-variables-envexample)
3. [Local Setup — Step by Step](#3-local-setup--step-by-step)
4. [Branching Workflow](#4-branching-workflow)
5. [Commands Reference](#5-commands-reference)
6. [Deployment](#6-deployment)
7. [Testing Strategy](#7-testing-strategy)
8. [Docker Compose (dev-with-postgres)](#8-docker-compose-dev-with-postgres)

---

## 1. Monorepo Directory Tree

```
hisaab/
├── .gitignore
├── .env.example                    # Canonical env template (committed)
├── README.md
├── docker-compose.yml              # Optional dev-with-postgres mode
│
├── contracts/
│   └── openapi.yaml                # Single source of truth for API contract
│
├── docs/
│   ├── DEVOPS_AND_SETUP.md         # This file
│   ├── PRD.md                      # Product Requirements Document
│   ├── ARCHITECTURE.md             # System architecture & data-flow diagrams
│   ├── API_DESIGN.md               # Endpoint-level API design notes
│   ├── DATA_MODELS.md              # Entity definitions & DB schema narrative
│   ├── FEATURES.md                 # Feature list & acceptance criteria
│   └── UI_UX_PLAN.md               # Wireframes narrative & component map
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env                        # Local overrides (git-ignored)
│   ├── .env.example                # Frontend-specific env template
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   ├── DashboardPage.tsx
│       │   ├── ContactsPage.tsx
│       │   ├── ContactDetailPage.tsx
│       │   ├── TransactionsPage.tsx
│       │   ├── DossierPage.tsx
│       │   ├── SettingsPage.tsx
│       │   └── NotFoundPage.tsx
│       ├── components/
│       │   ├── layout/
│       │   │   ├── Sidebar.tsx
│       │   │   ├── TopBar.tsx
│       │   │   └── PageShell.tsx
│       │   ├── dashboard/
│       │   │   ├── SummaryCards.tsx
│       │   │   ├── EscalationFeed.tsx
│       │   │   └── RecentActivity.tsx
│       │   ├── contacts/
│       │   │   ├── ContactCard.tsx
│       │   │   ├── ContactTable.tsx
│       │   │   └── ContactForm.tsx
│       │   ├── transactions/
│       │   │   ├── TransactionTable.tsx
│       │   │   ├── TransactionForm.tsx
│       │   │   └── TransactionFilters.tsx
│       │   └── shared/
│       │       ├── Button.tsx
│       │       ├── Modal.tsx
│       │       ├── Badge.tsx
│       │       ├── Spinner.tsx
│       │       ├── EmptyState.tsx
│       │       └── ErrorBoundary.tsx
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useContacts.ts
│       │   ├── useTransactions.ts
│       │   ├── useDossier.ts
│       │   ├── useEscalations.ts
│       │   └── useGmailSync.ts
│       ├── api/
│       │   ├── client.ts           # Axios / fetch base client
│       │   ├── auth.ts
│       │   ├── contacts.ts
│       │   ├── transactions.ts
│       │   ├── dossier.ts
│       │   └── sync.ts
│       ├── types/
│       │   ├── index.ts            # Re-exports
│       │   └── generated.ts        # Auto-generated from openapi.yaml (npm run gen:types)
│       ├── mocks/
│       │   ├── browser.ts          # MSW browser setup
│       │   ├── handlers/
│       │   │   ├── auth.ts
│       │   │   ├── contacts.ts
│       │   │   ├── transactions.ts
│       │   │   └── dossier.ts
│       │   └── data/
│       │       ├── contacts.ts     # Seed fixtures
│       │       └── transactions.ts
│       └── utils/
│           ├── currency.ts
│           ├── dates.ts
│           ├── formatters.ts
│           └── validators.ts
│
└── backend/
    ├── pyproject.toml              # PEP 517 build + dependency spec
    ├── .env                        # Local overrides (git-ignored)
    ├── mcp_server.py               # FastMCP entry point (MCP tool exposure)
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/               # Migration files (auto-generated)
    ├── tests/
    │   ├── conftest.py             # Shared fixtures, test DB setup
    │   ├── unit/
    │   │   ├── test_llm_router.py
    │   │   ├── test_escalation.py
    │   │   └── test_dossier_service.py
    │   └── integration/
    │       ├── test_contacts_router.py
    │       ├── test_transactions_router.py
    │       └── test_auth_router.py
    └── app/
        ├── main.py                 # FastAPI app factory, middleware, lifespan
        ├── config.py               # Pydantic Settings — reads .env
        ├── database.py             # SQLAlchemy async engine & session factory
        ├── dependencies.py         # FastAPI Depends helpers (db, current_user…)
        ├── routers/
        │   ├── __init__.py
        │   ├── auth.py             # /auth/google, /auth/callback, /auth/logout, /auth/me
        │   ├── contacts.py         # CRUD /contacts
        │   ├── transactions.py     # CRUD /transactions
        │   ├── dossier.py          # POST /dossier/generate, GET /dossier/{id}/pdf
        │   ├── sync.py             # POST /sync/gmail
        │   └── escalations.py      # GET /escalations
        ├── services/
        │   ├── __init__.py
        │   ├── contact_service.py
        │   ├── transaction_service.py
        │   ├── dossier_service.py
        │   ├── escalation_service.py
        │   ├── gmail_service.py
        │   └── pdf_service.py      # ReportLab PDF generation
        ├── models/
        │   ├── __init__.py
        │   ├── user.py
        │   ├── contact.py
        │   ├── transaction.py
        │   ├── dossier.py
        │   └── escalation_log.py
        ├── schemas/
        │   ├── __init__.py
        │   ├── auth.py
        │   ├── contact.py
        │   ├── transaction.py
        │   ├── dossier.py
        │   └── escalation.py
        ├── jobs/
        │   ├── __init__.py
        │   └── escalation_scheduler.py   # APScheduler background job
        ├── llm/
        │   ├── __init__.py
        │   ├── router.py           # Provider selection & fallback logic
        │   ├── providers/
        │   │   ├── groq.py
        │   │   ├── gemini.py
        │   │   └── mistral.py
        │   ├── cache.py            # In-memory / Redis LLM response cache
        │   └── prompts.py          # Prompt templates (dossier, categorisation)
        ├── auth/
        │   ├── __init__.py
        │   ├── google_oauth.py     # OAuth2 flow helpers
        │   ├── session.py          # httpOnly cookie session encode/decode
        │   └── demo.py             # Demo mode user injection
        └── utils/
            ├── __init__.py
            ├── pagination.py
            ├── exceptions.py
            └── logging.py
```

---

## 2. Environment Variables (.env.example)

Copy this file to `.env` in both the repo root and `backend/` before starting. **Never commit `.env`.**

```dotenv
# ─────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────
SECRET_KEY=                        # Random 32-byte hex; used for misc signing
ENVIRONMENT=development            # development | staging | production
LOG_LEVEL=INFO                     # DEBUG | INFO | WARNING | ERROR

# ─────────────────────────────────────────────────────────────
# Google OAuth
# ─────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=                  # From Google Cloud Console → OAuth 2.0 Credentials
GOOGLE_CLIENT_SECRET=              # From Google Cloud Console → OAuth 2.0 Credentials
GOOGLE_REDIRECT_URI=               # Must match Console redirect URI, e.g. http://localhost:8000/auth/callback

# ─────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./hisaab_dev.db
# For prod Postgres: postgresql+asyncpg://user:pass@host:5432/hisaab

# ─────────────────────────────────────────────────────────────
# LLM Providers  (populate at least one)
# ─────────────────────────────────────────────────────────────
GROQ_API_KEY=                      # https://console.groq.com
GEMINI_API_KEY=                    # https://aistudio.google.com/app/apikey
MISTRAL_API_KEY=                   # https://console.mistral.ai

# ─────────────────────────────────────────────────────────────
# LLM Config
# ─────────────────────────────────────────────────────────────
LLM_MAX_CONCURRENT=3               # Max simultaneous LLM requests
LLM_CACHE_TTL_SECONDS=86400        # How long to cache identical LLM responses (seconds)
LLM_TIMEOUT_SECONDS=30             # Per-request timeout for LLM calls

# ─────────────────────────────────────────────────────────────
# Escalation Thresholds (days overdue)
# ─────────────────────────────────────────────────────────────
ESCALATION_RUNG1_DAYS=7            # Rung 1: gentle reminder
ESCALATION_RUNG2_DAYS=21           # Rung 2: follow-up
ESCALATION_RUNG3_DAYS=45           # Rung 3: strong follow-up
ESCALATION_RUNG4_DAYS=46           # Rung 4: escalate / legal notice flag

# ─────────────────────────────────────────────────────────────
# Gmail Sync
# ─────────────────────────────────────────────────────────────
GMAIL_SYNC_LOOKBACK_DAYS=90        # How far back to scan Gmail on first sync
GMAIL_SYNC_MAX_PAGES=50            # Max Gmail API pages per sync run

# ─────────────────────────────────────────────────────────────
# Frontend (Vite — must be prefixed VITE_)
# ─────────────────────────────────────────────────────────────
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_DEMO_SIMULATOR=true    # Set false to disable the demo mode UI toggle

# ─────────────────────────────────────────────────────────────
# Session
# ─────────────────────────────────────────────────────────────
SESSION_COOKIE_NAME=hisaab_session
SESSION_COOKIE_SECURE=false        # true in production (HTTPS required)
SESSION_JWT_SECRET=                # Random 32-byte hex; signs session JWTs
```

> [!CAUTION]
> `SECRET_KEY` and `SESSION_JWT_SECRET` must be unique, random, and **never reused across environments**. Generate them with `python -c "import secrets; print(secrets.token_hex(32))"`.

---

## 3. Local Setup — Step by Step

### 3.1 Prerequisites

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Git | 2.40+ | https://git-scm.com |
| Node.js | 20 LTS | https://nodejs.org |
| npm | 10+ (bundled with Node 20) | — |
| Python | 3.12 | https://python.org |
| (Optional) Docker | 24+ | https://docker.com (only for postgres dev mode) |

Verify versions:

```bash
git --version
node --version    # v20.x.x
npm --version     # 10.x.x
python --version  # Python 3.12.x
```

---

### 3.2 Clone the Repository

```bash
git clone https://github.com/<org>/hisaab.git
cd hisaab
```

---

### 3.3 Backend Setup

```bash
# 1. Create and activate a virtual environment
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 2. Install the package in editable mode with dev extras
pip install -e ".[dev]"

# 3. Copy and configure environment variables
cp ../.env.example .env
# Edit .env — fill in SECRET_KEY, SESSION_JWT_SECRET, and at least one LLM key.
# For Google OAuth, leave keys blank during pure-backend testing;
# demo mode works without them.

# 4. Run database migrations
alembic upgrade head

# 5. Seed demo data (creates demo user + sample contacts/transactions)
python -m app.utils.seed_demo
```

> [!NOTE]
> The seed script is idempotent — safe to run multiple times. It detects the demo user by a fixed email and skips re-creation.

---

### 3.4 Frontend Setup

```bash
# From the repo root (new terminal, leave backend terminal running)
cd frontend

# 1. Install dependencies
npm install

# 2. Copy and configure environment variables
cp .env.example .env
# VITE_API_BASE_URL defaults to http://localhost:8000 — no change needed for local dev.
# Set VITE_ENABLE_DEMO_SIMULATOR=true to show the demo toggle in the UI.
```

---

### 3.5 Start Both Servers

**Terminal A — Backend:**

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
uvicorn app.main:app --reload --port 8000
```

**Terminal B — Frontend:**

```bash
cd frontend
npm run dev
# Vite starts at http://localhost:5173 by default
```

Open `http://localhost:5173` in your browser.

---

### 3.6 MSW — Mocks vs Real Backend

The frontend ships with [Mock Service Worker (MSW)](https://mswjs.io/) handlers under `src/mocks/`.

| Mode | When to use | How to enable |
|------|-------------|---------------|
| **Real backend** | Integration work, testing OAuth, full E2E | Default when backend is running; `VITE_ENABLE_DEMO_SIMULATOR=false` |
| **MSW mocks** | Frontend-only feature development; backend not running | Set `VITE_ENABLE_DEMO_SIMULATOR=true` and start the app — MSW intercepts all API calls |
| **Hybrid** | Some endpoints mocked, others real | Comment out specific handlers in `src/mocks/handlers/` |

MSW is initialised in `src/main.tsx` only when `import.meta.env.VITE_ENABLE_DEMO_SIMULATOR === 'true'` and `import.meta.env.MODE !== 'production'`.

> [!TIP]
> Run `npm run dev` with `VITE_ENABLE_DEMO_SIMULATOR=true` and no backend running to do pure UI work. Switch to real backend for contract validation.

---

## 4. Branching Workflow

```
main
 └── develop
      ├── feature/dev1/<ticket-or-name>
      └── feature/dev2/<ticket-or-name>
```

### Branch Rules

| Branch | Purpose | Protected? | Merge strategy |
|--------|---------|-----------|----------------|
| `main` | Production-ready, tagged releases | ✅ Yes | Squash merge from `develop` |
| `develop` | Integration — always deployable to staging | ✅ Yes | Squash merge from feature branches |
| `feature/dev1/*` | Dev 1 (frontend) work | ❌ No | PR → `develop` |
| `feature/dev2/*` | Dev 2 (backend) work | ❌ No | PR → `develop` |

### Naming Conventions

```
feature/dev1/gmail-sync-ui
feature/dev1/contacts-filter
feature/dev2/llm-router
feature/dev2/pdf-dossier
feature/dev2/escalation-scheduler
```

### Pull Request Rules

1. **Target:** Always open PRs against `develop`, never directly to `main`.
2. **Review:** At least one approval required (the other developer).
3. **CI must pass** before merge (lint + type check + tests).
4. **Squash merge** to keep `develop` history linear.
5. `develop` → `main` is a **squash merge** performed only at release time, tagged with a semver version (`v0.1.0`, `v0.2.0` …).

### Contract Changes

> [!IMPORTANT]
> Any PR that modifies `contracts/openapi.yaml` **must**:
> 1. Be labelled `contract-change` in GitHub.
> 2. Update `contracts/openapi.yaml` **before** implementing frontend or backend changes (spec-first).
> 3. Require approval from **both** Dev 1 and Dev 2 before merge.
> 4. Trigger `npm run gen:types` on the frontend side so `src/types/generated.ts` stays in sync.

---

## 5. Commands Reference

### Backend

| Task | Command |
|------|---------|
| Run dev server | `uvicorn app.main:app --reload --port 8000` |
| Run tests | `pytest` |
| Run tests with coverage | `pytest --cov=app --cov-report=term-missing` |
| Lint | `ruff check .` |
| Lint + auto-fix | `ruff check . --fix` |
| Format | `ruff format .` |
| Type check | `mypy app/` |
| Create new migration | `alembic revision --autogenerate -m "describe change"` |
| Apply migrations | `alembic upgrade head` |
| Downgrade one step | `alembic downgrade -1` |
| Show current revision | `alembic current` |
| Show migration history | `alembic history --verbose` |
| Start MCP server | `python mcp_server.py` |

> [!NOTE]
> Run all backend commands from the `backend/` directory with the virtual environment activated.

### Frontend

| Task | Command |
|------|---------|
| Start dev server | `npm run dev` |
| Production build | `npm run build` |
| Preview production build | `npm run preview` |
| Run unit tests | `npm run test` |
| Run tests (watch mode) | `npm run test:watch` |
| Lint | `npm run lint` |
| Type check | `npm run typecheck` |
| Generate TS types from OpenAPI | `npm run gen:types` |

> [!NOTE]
> `npm run gen:types` reads `../contracts/openapi.yaml` and writes `src/types/generated.ts`. Run this after every `contract-change` PR is merged.

---

## 6. Deployment

### Target Environments

| Environment | Backend | Frontend | Database |
|-------------|---------|----------|----------|
| Local dev | uvicorn --reload | Vite dev server | SQLite |
| Dev-with-postgres | uvicorn --reload | Vite dev server | Postgres (Docker) |
| Production | gunicorn + uvicorn workers behind nginx | Static build on nginx / Vercel / Netlify | Postgres |

### Backend (Production)

```bash
# Install production dependencies only
pip install -e "."

# Start with gunicorn (4 uvicorn worker processes)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

Nginx reverse-proxy config (minimal):

```nginx
server {
    listen 80;
    server_name api.hisaab.app;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name api.hisaab.app;

    ssl_certificate     /etc/letsencrypt/live/api.hisaab.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.hisaab.app/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

### Frontend (Production)

```bash
cd frontend
npm run build      # Outputs to frontend/dist/
```

Serve `dist/` as static files from nginx, or push directly to **Vercel / Netlify** (auto-detects Vite).

Set the following env vars on the hosting platform:
- `VITE_API_BASE_URL=https://api.hisaab.app`
- `VITE_ENABLE_DEMO_SIMULATOR=false`

### Database (Production — Postgres)

- Use `postgresql+asyncpg://` as the `DATABASE_URL`.
- Run `alembic upgrade head` as part of the deploy pipeline before starting the app server.
- Connection pooling is handled by SQLAlchemy's `asyncpg` pool; set `pool_size=10, max_overflow=20` in `app/database.py` for production.
- Use a managed Postgres service (Railway, Render Postgres, Supabase, or self-hosted) with daily automated backups.

### Secrets Management

> [!CAUTION]
> Never commit secrets to the repository. All secrets must be provided through environment variables or a secrets manager (e.g., Railway / Render secret stores, AWS Secrets Manager, Doppler).

Checklist before every deploy:

- [ ] `SECRET_KEY` and `SESSION_JWT_SECRET` are unique per environment
- [ ] `SESSION_COOKIE_SECURE=true` in production
- [ ] `ENVIRONMENT=production`
- [ ] `DATABASE_URL` points to production Postgres
- [ ] Google OAuth redirect URIs updated in Google Cloud Console to match production domain

### SSL / TLS

- **Self-hosted VPS:** Use [Certbot](https://certbot.eff.org/) with Let's Encrypt. Renews automatically.
- **Railway / Render / Vercel / Netlify:** SSL is platform-managed; no configuration needed.

---

## 7. Testing Strategy

### Backend

**Framework:** `pytest` + `pytest-asyncio` + `httpx` (async test client)

| Layer | Approach | Location |
|-------|----------|----------|
| Unit — services | Test service functions in isolation; mock DB session and external calls | `tests/unit/` |
| Integration — routers | Full request/response cycle with test SQLite DB; real SQLAlchemy sessions | `tests/integration/` |
| LLM calls | Mock `httpx.AsyncClient` responses; test router fallback logic | `tests/unit/test_llm_router.py` |
| Auth | Mock Google OAuth token exchange; test session cookie creation | `tests/integration/test_auth_router.py` |

Key pytest fixtures (defined in `tests/conftest.py`):

```python
# Async test DB (in-memory SQLite, reset per test session)
@pytest_asyncio.fixture(scope="session")
async def test_db(): ...

# Authenticated async HTTP client
@pytest_asyncio.fixture
async def auth_client(test_db): ...

# Demo user fixture
@pytest_asyncio.fixture
async def demo_user(test_db): ...
```

Run the full suite:

```bash
pytest -v --cov=app --cov-report=term-missing
```

### Frontend

**Framework:** Vitest + React Testing Library + MSW

| Layer | Approach | Location |
|-------|----------|----------|
| Component tests | Render with RTL; assert DOM state and interactions | `src/components/**/*.test.tsx` |
| Hook tests | `renderHook`; MSW intercepts API calls | `src/hooks/**/*.test.ts` |
| Page tests | Render full page with router; mock auth state | `src/pages/**/*.test.tsx` |
| API client tests | Assert request shape; MSW validates handlers | `src/api/**/*.test.ts` |

MSW handlers in `src/mocks/handlers/` are shared between dev mode and tests — same contract, no duplication.

```bash
npm run test            # single run
npm run test:watch      # watch mode during development
```

### End-to-End (Phase 2)

**Framework:** Playwright

Planned smoke test suite (post-MVP):

```
1. Login via Google OAuth (stubbed OAuth server in test env)
2. Trigger Gmail sync and wait for completion indicator
3. Navigate to Dashboard — assert summary cards render
4. Open a contact's detail page — assert transaction list loads
5. Generate a dossier — assert PDF download link appears
```

Run E2E (once configured):

```bash
npx playwright test
npx playwright test --ui    # interactive mode
```

---

## 8. Docker Compose (dev-with-postgres)

SQLite is the **default** for local development — no Docker required. Use this `docker-compose.yml` only when you need to test Postgres-specific behaviour (e.g., migration ordering, asyncpg connection pool, full-text search).

```yaml
# docker-compose.yml  (repo root)
# Usage:
#   docker compose up -d          # start Postgres in background
#   # Then run backend normally:  uvicorn app.main:app --reload --port 8000
#   docker compose down           # stop and remove containers
#   docker compose down -v        # also wipe the postgres volume

version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    container_name: hisaab_postgres_dev
    restart: unless-stopped
    environment:
      POSTGRES_USER: hisaab
      POSTGRES_PASSWORD: hisaab_dev_password
      POSTGRES_DB: hisaab_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hisaab -d hisaab_dev"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev        # lightweight dev image (optional)
    container_name: hisaab_backend_dev
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://hisaab:hisaab_dev_password@postgres:5432/hisaab_dev
      ENVIRONMENT: development
      LOG_LEVEL: DEBUG
      # Remaining secrets come from .env via env_file:
    env_file:
      - ./backend/.env
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app              # live-reload source mount
    command: >
      uvicorn app.main:app
        --host 0.0.0.0
        --port 8000
        --reload
        --reload-dir /app/app

volumes:
  postgres_data:
    driver: local
```

> [!NOTE]
> When using Docker Compose, set `DATABASE_URL=postgresql+asyncpg://hisaab:hisaab_dev_password@postgres:5432/hisaab_dev` in `backend/.env`. The `DATABASE_URL` in the compose `environment` block takes precedence over the `.env` file value when both are present in the `backend` service.

> [!TIP]
> You do **not** need to run the backend inside Docker. The most common workflow is:
> `docker compose up -d postgres` (start just the DB), then run `uvicorn` natively in your virtualenv pointing to `postgresql+asyncpg://hisaab:hisaab_dev_password@localhost:5432/hisaab_dev`.

---

*Last updated: 2026-11-26 — Hisaab v0.1 development phase.*
