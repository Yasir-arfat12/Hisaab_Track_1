# Hisaab — Progress Tracker

> Check off items as they are completed. Update this file in the same PR as the implementation. Last updated: <!-- date -->

---

## Backend Checklist

### Project Setup

- [ ] FastAPI scaffold + `pyproject.toml` (Python 3.12, all deps pinned)
- [ ] Alembic init + first migration (`initial` schema)
- [ ] All DB models created (`User`, `OAuthToken`, `EmailMessage`, `Promise`, `BankCredit`, `EscalationEvent`, `Dossier`, `Job`, `LlmCache`)
- [ ] Health endpoint (`GET /health` → `{"status":"ok","version":"..."}`)
- [ ] Structured JSON logging middleware (request-ID, latency, level)
- [ ] Request ID middleware (`X-Request-ID` header in/out)

### Auth

- [ ] Google OAuth start endpoint (`POST /auth/google/start`)
- [ ] Google OAuth callback + session cookie (`GET /auth/google/callback`)
- [ ] Demo Mode endpoint + seed data (`POST /auth/demo`)
- [ ] Logout endpoint (`POST /auth/logout`)
- [ ] Auth/me endpoint (`GET /auth/me`)
- [ ] Token encryption (AES-256-GCM for stored OAuth tokens)

### Gmail Sync

- [ ] Gmail connect endpoint (`POST /gmail/connect`)
- [ ] Gmail disconnect + purge endpoint (`POST /gmail/disconnect`)
- [ ] Background sync job (paginated, 90-day window, idempotent by message-ID)
- [ ] Gmail status endpoint (`GET /gmail/status`)

### Promise Extraction

- [ ] LLM router (chain: primary → fallback → fallback; cooldown on failure)
- [ ] LLM cache (`llm_cache` table; cache key = prompt hash)
- [ ] `extract_promises` service (validation: substring check, amount present in quote, date parseable)
- [ ] Prompt injection detection (pre-LLM filter; logs and rejects)
- [ ] `Job` table + job status endpoint (`GET /jobs/{id}`)

### Bank Credits

- [ ] Email bank alert parser (regex-based amount + merchant extraction)
- [ ] CSV upload endpoint + column validation (`POST /credits/upload`)
- [ ] Credits list endpoint (`GET /credits`)

### Verification

- [ ] `verify_fulfillment` (amount tolerance ±2%, fuzzy merchant name, ±7-day date window)
- [ ] Ambiguous match detection (never auto-close; returns `AMBIGUOUS` status)
- [ ] Re-verify endpoint (`POST /promises/{id}/re-verify`)

### Escalation

- [ ] Deterministic rung + deadline math (calendar-day arithmetic, no randomness)
- [ ] LLM draft generation (with mandatory not-legal-advice notice in output)
- [ ] Next step endpoint (`GET /promises/{id}/escalation/next-step`)
- [ ] Draft endpoint (`POST /promises/{id}/escalation/draft`)

### Dossier

- [ ] ReportLab PDF builder (promise history, escalation log, credits, merchant record sections)
- [ ] Dossier generate endpoint — background job (`POST /promises/{id}/dossier`)
- [ ] Dossier download endpoint (`GET /promises/{id}/dossier`)

### Dashboard + Merchant

- [ ] Dashboard summary endpoint (`GET /dashboard/summary` — owed total, overdue count, counts by status)
- [ ] Merchant record endpoint (`GET /merchants/{name}`)

### MCP Server

- [ ] FastMCP mount at `/mcp`
- [ ] Tool: `extract_promises`
- [ ] Tool: `verify_fulfillment`
- [ ] Tool: `next_escalation_step`
- [ ] Tool: `build_dossier`
- [ ] Tool: `check_merchant_record`

### Demo Simulator

- [ ] `POST /simulate` endpoint (all 4 scenarios: fulfilled, escalated, ambiguous, dossier-ready)

### Security + Ops

- [ ] Idempotency keys middleware (`Idempotency-Key` header; 24-hour window)
- [ ] Rate limiting (per-user, configurable; 429 with `Retry-After`)
- [ ] User delete + data purge cascade (`DELETE /auth/account`; all related rows removed)
- [ ] Input validation — strict Pydantic (no extra fields allowed; all fields typed)
- [ ] Error handler for all defined error codes (standardised `{"error": {"code": "...", "message": "..."}}`)

---

## Frontend Checklist

### Project Setup

- [ ] Vite + React 18 + TypeScript scaffold
- [ ] Tailwind CSS config (content globs, theme extensions)
- [ ] React Router setup (all routes defined in `src/router.tsx`)
- [ ] TanStack Query setup (`QueryClientProvider` in `src/main.tsx`, devtools in dev)
- [ ] MSW setup (`public/mockServiceWorker.js` initialised; `src/mocks/handlers.ts` with stubs for all 25+ endpoints)
- [ ] TS types generated from `contracts/openapi.yaml` → `src/types/api.ts`
- [ ] Typed API fetcher (`src/lib/api.ts` wrapping fetch/axios with typed request/response)

### Auth Pages

- [ ] `/login` page (Google OAuth button + Demo Mode button)
- [ ] `/auth/callback` handler (exchanges code for session, stores auth state, redirects)
- [ ] Session-aware route guards (`<RequireAuth>` component; redirects unauthenticated users to `/login`)

### Dashboard

- [ ] Summary cards (total owed, overdue count, promise counts by status)
- [ ] Promise list with filters (status, category, date range)
- [ ] Cursor-based pagination (Load More or infinite scroll)
- [ ] Loading state (skeleton cards)
- [ ] Error state (error boundary + retry button)
- [ ] Empty state (no promises illustration + onboarding CTA)

### Promise Detail

- [ ] Promise header (merchant name, amount, status badge, due date)
- [ ] Timeline component (chronological event list with icons)
- [ ] Escalation section (next step display + "Generate Draft" button)
- [ ] Dossier download button (triggers background job + polls status + downloads PDF)
- [ ] Dismiss action (with confirmation dialog)

### Credits

- [ ] CSV upload form (react-hook-form + zod schema; file input; column validation feedback)
- [ ] Credits list (table of parsed credits with amount, merchant, date)

### Merchant Record

- [ ] Stats display (promise count, fulfilment rate, escalation history)

### Settings

- [ ] Gmail disconnect (button + confirmation; clears sync state)
- [ ] Delete account (button + confirmation dialog with "type DELETE to confirm" UX)

### Demo Simulator

- [ ] Scenario buttons (4 scenarios: fulfilled, escalated, ambiguous, dossier-ready)
- [ ] Result display (shows promise state after simulation)

### Design System

- [ ] `StatusBadge` component (colour-coded badge per promise status)
- [ ] `AmountDisplay` (paise → ₹ with `Intl.NumberFormat` locale formatting)
- [ ] `DateDisplay` (UTC → IST display; relative labels for recent dates)
- [ ] `TimelineItem` (icon slot, timestamp, description, connector line)
- [ ] `EscalationRungBadge` (rung 1/2/3 with colour progression)
- [ ] `ConfidenceMeter` (0–100 visual bar with colour bands)

---

## Contracts Checklist

- [ ] `/contracts/openapi.yaml` complete (all 25+ endpoints, all schemas, all error responses)
- [ ] `/docs/API_CONTRACT.md` complete (human-readable summary of every endpoint)
- [ ] TS types generated from `openapi.yaml` and committed to `frontend/src/types/api.ts`
- [ ] MSW mock handlers cover every endpoint defined in `openapi.yaml`
- [ ] Demo story seed data included in `openapi.yaml` `examples` sections

---

## Documentation Checklist

- [ ] `docs/PROJECT_PLAN.md` — vision, goals, non-goals, feature list
- [ ] `docs/FRONTEND.md` — architecture decisions, folder structure, conventions
- [ ] `docs/BACKEND.md` — architecture decisions, folder structure, service layer guide
- [ ] `docs/DEVOPS_AND_SETUP.md` — local dev setup, env vars, running tests, deployment
- [ ] `docs/API_CONTRACT.md` — human-readable endpoint reference
- [ ] `docs/EXECUTION_GUIDE.md` — this dev playbook ✅
- [ ] `docs/PROGRESS.md` — this tracker ✅
- [ ] `docs/AUDIT.md` — security/compliance audit log (clean on release)
- [ ] `docs/ASSUMPTIONS.md` — documented assumptions and open questions
- [ ] `README.md` (repo root) — quick start, monorepo structure, links to docs

---

## Release Gate

Before merging `develop` → `main` for any release, all of the following must be true:

- [ ] All Backend Checklist items above are checked
- [ ] All Frontend Checklist items above are checked
- [ ] All Contracts Checklist items above are checked
- [ ] All Documentation Checklist items above are checked
- [ ] `pytest` passes with 0 failures (unit + integration)
- [ ] `vitest` passes with 0 failures
- [ ] No `.env` files committed (`git grep -r "SECRET_KEY\s*=" -- :!*.example` returns nothing)
- [ ] `AUDIT.md` reviewed and marked clean
- [ ] Demo Mode works end-to-end without any real credentials
