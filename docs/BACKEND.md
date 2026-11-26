# Hisaab — Backend Planning

> **Stack:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) · Alembic · FastMCP · ReportLab · httpx · cryptography

---

## 1. Architecture & Folder Structure

```
backend/
  app/
    main.py              # FastAPI app factory, router registration, lifespan hooks
    config.py            # pydantic-settings Settings class (reads .env)
    database.py          # Async SQLAlchemy engine, session factory, Base
    models/
      user.py            # User, OAuthToken, GmailSyncState
      email.py           # Email
      promise.py         # Promise, Merchant
      finance.py         # BankCredit, VerificationMatch
      escalation.py      # EscalationStep
      job.py             # Job
      cache.py           # LlmCache, IdempotencyKey
    schemas/
      auth.py            # AuthMeResponse, DemoLoginResponse
      promise.py         # PromiseCreate, PromiseResponse, PromisePatch
      merchant.py        # MerchantResponse
      finance.py         # BankCreditResponse, VerificationMatchResponse
      escalation.py      # EscalationStepResponse, EscalationDraftRequest
      dashboard.py       # DashboardSummaryResponse
      job.py             # JobResponse
      common.py          # Envelope[T], CursorPage[T], ErrorDetail
    routers/
      auth.py            # /auth/* (AUTH_ME, google OAuth, demo, logout)
      gmail.py           # /gmail/* (sync trigger, sync status)
      promises.py        # /promises/* (PROMISE_LIST, GET, PATCH, DISMISS)
      merchants.py       # /merchants/* (MERCHANT_GET)
      bank_credits.py    # /credits/* (POST /credits/upload, GET /credits)
      escalation.py      # /escalation/* (ESCALATION_LIST, ESCALATION_DRAFT)
      dashboard.py       # /dashboard/*
      jobs.py            # /jobs/:id (JOB_GET)
      demo.py            # /demo/* (simulate email, credit, reset, time-warp)
    services/
      promise_service.py      # extract_promises, patch, dismiss, list
      verification_service.py # verify_fulfillment, match_credits
      escalation_service.py   # build ladder, generate draft, advance rung
      gmail_service.py        # sync emails, history delta, token refresh
      merchant_service.py     # upsert, normalize, stats
      credit_service.py       # CSV parse+ingest, dedup, list
      dossier_service.py      # build dossier JSON + PDF (ReportLab)
      user_service.py         # upsert user, delete account, revoke token
    jobs/
      sync_job.py        # Full Gmail sync BackgroundTask
      csv_job.py         # CSV ingestion BackgroundTask
      extraction_job.py  # Batch LLM extraction BackgroundTask
    llm/
      router.py          # Provider chain, failover, semaphore, cache lookup
      providers/
        groq.py          # Groq client (gpt-oss-120b, gpt-oss-20b)
        gemini.py        # Gemini client (gemini-3.5-flash-lite)
        mistral.py       # Mistral client (ministral-8b-latest)
        deterministic.py # Regex/rule-based fallback extractor
      prompts.py         # Prompt templates (extraction, escalation draft)
      guard.py           # Prompt injection detection
    mcp_server.py        # FastMCP instance + 5 tool definitions
    auth/
      oauth.py           # Google OAuth flow (start, callback, token exchange)
      session.py         # Signed JWT session creation/validation
      demo.py            # Demo user creation + seed data
      dependencies.py    # get_current_user FastAPI dependency
    utils/
      email_parser.py    # RFC 2822 parsing, body extraction, dedup hash
      fuzzy.py           # rapidfuzz merchant name matching helpers
      pdf.py             # ReportLab PDF builder (dossier export)
      encryption.py      # AES-256-GCM encrypt/decrypt (token storage)
      pagination.py      # Cursor pagination helpers
      rate_limit.py      # Per-user per-endpoint rate limiting middleware
  alembic/
    env.py
    versions/            # Migration scripts
  tests/
    conftest.py          # pytest fixtures, async test client, test DB
    unit/                # Service-layer unit tests (mocked DB)
    integration/         # Router tests via httpx AsyncClient
    llm/                 # LLM router failover tests (mocked providers)
  pyproject.toml
  .env.example
```

### 1.1 `main.py` Responsibilities

```python
app = FastAPI(title="Hisaab API", version="1.0.0")

# Lifespan: create DB tables (dev), run startup checks
@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield
    await engine.dispose()

# Routers
app.include_router(auth_router,         prefix="/api/v1")
app.include_router(gmail_router,        prefix="/api/v1")
app.include_router(promises_router,     prefix="/api/v1")
app.include_router(merchants_router,    prefix="/api/v1")
app.include_router(bank_credits_router, prefix="/api/v1")
app.include_router(escalation_router,   prefix="/api/v1")
app.include_router(dashboard_router,    prefix="/api/v1")
app.include_router(jobs_router,         prefix="/api/v1")
app.include_router(demo_router,         prefix="/api/v1")

# MCP mounted at /mcp
app.mount("/mcp", mcp_app)

# Exception handlers, CORS, request-id middleware, rate limiting
```

### 1.2 `config.py` (pydantic-settings)

Key settings:

| Setting | Type | Notes |
|---|---|---|
| `DATABASE_URL` | str | SQLite in dev, Postgres in prod |
| `SECRET_KEY` | SecretStr | 32-byte key for AES + JWT signing |
| `GOOGLE_CLIENT_ID` | str | OAuth credential |
| `GOOGLE_CLIENT_SECRET` | SecretStr | OAuth credential |
| `GOOGLE_REDIRECT_URI` | str | Must match Google Console |
| `LLM_PROVIDERS` | list[str] | Ordered provider chain |
| `LLM_MAX_CONCURRENT` | int | Default 3 |
| `LLM_CACHE_TTL_SECONDS` | int | Default 86400 |
| `ESCALATION_THRESHOLDS_DAYS` | list[int] | `[7, 21, 45]` |
| `NOT_LEGAL_ADVICE_TEXT` | str | Appended to all drafts |
| `RATE_LIMIT_DEFAULT` | str | e.g. `"60/minute"` |
| `ENVIRONMENT` | Literal['dev','staging','prod'] | Controls debug, MSW, demo routes |

---

## 2. Full Database Schema

> All tables use UUID primary keys. `created_at` / `updated_at` default to `now()` UTC. Soft-delete via `deleted_at` where noted.

### 2.1 `users`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `email` | VARCHAR(254) | UNIQUE NOT NULL | |
| `name` | VARCHAR(255) | NOT NULL | |
| `picture_url` | TEXT | NULLABLE | |
| `is_demo` | BOOLEAN | NOT NULL DEFAULT false | Demo accounts |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `deleted_at` | TIMESTAMPTZ | NULLABLE | Soft-delete; triggers cascade purge |

**Indexes:** `email` (unique), `deleted_at` (partial index where null).

---

### 2.2 `oauth_tokens`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id ON DELETE CASCADE | |
| `provider` | VARCHAR(50) | NOT NULL DEFAULT 'google' | |
| `access_token_enc` | TEXT | NOT NULL | AES-256-GCM encrypted |
| `refresh_token_enc` | TEXT | NULLABLE | AES-256-GCM encrypted |
| `expires_at` | TIMESTAMPTZ | NULLABLE | |
| `scope` | TEXT | NOT NULL | Space-separated scopes |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `(user_id, provider)` unique.
**Notes:** Tokens encrypted with `utils/encryption.py` using `SECRET_KEY`; never stored in plaintext; `expires_at` checked before every Gmail API call.

---

### 2.3 `gmail_sync_state`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id UNIQUE ON DELETE CASCADE | One row per user |
| `last_synced_at` | TIMESTAMPTZ | NULLABLE | |
| `last_history_id` | VARCHAR(50) | NULLABLE | Gmail History API cursor |
| `next_page_token` | VARCHAR(255) | NULLABLE | For resumable list calls |
| `status` | ENUM('idle','running','failed') | NOT NULL DEFAULT 'idle' | |

**Indexes:** `user_id` (unique).

---

### 2.4 `emails`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id ON DELETE CASCADE | |
| `gmail_message_id` | VARCHAR(100) | UNIQUE NOT NULL | Dedup key |
| `thread_id` | VARCHAR(100) | NULLABLE | |
| `sender` | VARCHAR(500) | NOT NULL | |
| `subject` | TEXT | NULLABLE | |
| `received_at` | TIMESTAMPTZ | NOT NULL | |
| `body_hash` | VARCHAR(64) | NOT NULL | SHA-256 of body for dedup |
| `body_text` | TEXT | NULLABLE | Purged to NULL after extraction |
| `processed_at` | TIMESTAMPTZ | NULLABLE | Null = not yet sent to LLM |
| `purged_at` | TIMESTAMPTZ | NULLABLE | Timestamp of body purge |

**Indexes:** `gmail_message_id` (unique), `(user_id, processed_at)`, `body_hash`.
**Notes:** `body_text` set to `NULL` after `extract_promises` completes (`purge_email_body` called in service); `purged_at` records when.

---

### 2.5 `promises`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id ON DELETE CASCADE | |
| `email_id` | UUID | FK → emails.id NULLABLE | Null for manually-added |
| `merchant_id` | UUID | FK → merchants.id | |
| `merchant_name` | VARCHAR(255) | NOT NULL | Denormalized for display |
| `category` | VARCHAR(100) | NULLABLE | e.g. "refund", "delivery" |
| `amount_paise` | BIGINT | NULLABLE | Paise (100 paise = ₹1) |
| `due_date` | DATE | NULLABLE | |
| `exact_quote` | TEXT | NOT NULL | Literal substring from email |
| `confidence` | FLOAT | NOT NULL | 0.0–1.0 from LLM |
| `status` | ENUM | NOT NULL | See status values below |
| `extraction_method` | ENUM('llm','deterministic') | NOT NULL | |
| `needs_review_reason` | TEXT | NULLABLE | Why flagged for review |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |
| `dismissed_at` | TIMESTAMPTZ | NULLABLE | |
| `user_note` | TEXT | NULLABLE | Free-text note by user |

**Status ENUM values:** `pending`, `kept`, `overdue`, `needs_review`, `dismissed`

**Indexes:** `(user_id, status)`, `(user_id, merchant_id)`, `due_date`, `(user_id, created_at DESC)`.

---

### 2.6 `bank_credits`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id ON DELETE CASCADE | |
| `source` | ENUM('email','csv') | NOT NULL | |
| `amount_paise` | BIGINT | NOT NULL | |
| `credited_at` | TIMESTAMPTZ | NOT NULL | |
| `narration` | TEXT | NOT NULL | Bank statement line |
| `raw_line` | TEXT | NULLABLE | Original CSV row (CSV source) |
| `credit_hash` | VARCHAR(64) | UNIQUE NOT NULL | SHA-256(user_id+amount+date+narration) for dedup |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Indexes:** `credit_hash` (unique), `(user_id, credited_at DESC)`, `(user_id, amount_paise)`.

---

### 2.7 `verification_matches`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `promise_id` | UUID | FK → promises.id ON DELETE CASCADE | |
| `credit_id` | UUID | FK → bank_credits.id ON DELETE CASCADE | |
| `match_score` | FLOAT | NOT NULL | Composite score 0.0–1.0 |
| `matched_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `is_ambiguous` | BOOLEAN | NOT NULL DEFAULT false | Multiple credits matched |

**Indexes:** `promise_id`, `credit_id`, `(promise_id, is_ambiguous)`.
**Constraint:** `UNIQUE(promise_id, credit_id)`.

---

### 2.8 `escalation_steps`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `promise_id` | UUID | FK → promises.id ON DELETE CASCADE | |
| `rung` | SMALLINT | NOT NULL | 1–4 |
| `deadline` | DATE | NOT NULL | Computed from rung thresholds |
| `draft_text` | TEXT | NULLABLE | LLM-generated draft |
| `draft_generated_at` | TIMESTAMPTZ | NULLABLE | |
| `notice_type` | VARCHAR(100) | NOT NULL | e.g. "polite_nudge", "nch_draft" |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Indexes:** `promise_id`, `(promise_id, rung)` unique.

---

### 2.9 `merchants`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `name` | VARCHAR(255) | NOT NULL | Display name |
| `normalized_name` | VARCHAR(255) | NOT NULL | Lowercase, stripped |
| `domain` | VARCHAR(255) | NULLABLE | e.g. "amazon.in" |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Indexes:** `normalized_name` (unique), `domain`.

---

### 2.10 `jobs`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK → users.id ON DELETE CASCADE | |
| `type` | ENUM('gmail_sync','csv_ingest','extraction') | NOT NULL | |
| `status` | ENUM('pending','running','done','failed') | NOT NULL DEFAULT 'pending' | Mapped to `queued`/`completed` in API serializer |
| `progress` | SMALLINT | NOT NULL DEFAULT 0 | 0–100 percentage |
| `result_json` | JSONB / TEXT | NULLABLE | Summary of job output |
| `error_msg` | TEXT | NULLABLE | |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |
| `idempotency_key` | VARCHAR(255) | UNIQUE NULLABLE | Prevents duplicate job creation |

**Indexes:** `(user_id, status)`, `idempotency_key` (unique partial where not null), `(user_id, type, created_at DESC)`.

---

### 2.11 `llm_cache`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `prompt_hash` | VARCHAR(64) | UNIQUE NOT NULL | SHA-256 of normalized prompt |
| `provider` | VARCHAR(50) | NOT NULL | |
| `model` | VARCHAR(100) | NOT NULL | |
| `response_json` | TEXT | NOT NULL | Raw LLM JSON output |
| `tokens_used` | INT | NULLABLE | |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `expires_at` | TIMESTAMPTZ | NOT NULL | `created_at + LLM_CACHE_TTL` |

**Indexes:** `prompt_hash` (unique), `expires_at` (for TTL cleanup cron).

---

### 2.12 `idempotency_keys`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `key` | VARCHAR(255) | PK | Client-supplied `Idempotency-Key` header |
| `user_id` | UUID | FK → users.id ON DELETE CASCADE | |
| `endpoint` | VARCHAR(255) | NOT NULL | e.g. `POST /promises` |
| `response_json` | TEXT | NOT NULL | Cached full response body |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `expires_at` | TIMESTAMPTZ | NOT NULL | TTL 24 h |

**Indexes:** `key` (PK), `(user_id, endpoint)`, `expires_at`.

---

## 3. Business Logic

### 3.1 `extract_promises` (promise_service.py)

```
Input: email row (id, body_text, sender, received_at)

1. Build extraction prompt (prompts.py) with email body
2. Call llm_router.call(prompt, schema=ExtractionOutput)
3. For each candidate returned:
   a. VALIDATE exact_quote: must be literal substring of body_text
   b. VALIDATE amount: if amount_paise set, digits must appear in exact_quote
   c. VALIDATE due_date: parse as ISO 8601; reject unparseable
   d. Flag needs_review if confidence < 0.6 OR prompt_injection detected
4. Upsert merchant (normalized_name via utils/fuzzy.py)
5. INSERT promises; mark email.processed_at = now()
6. Purge email.body_text = NULL; set purged_at = now()
7. Trigger verify_fulfillment for each new promise (BackgroundTask)
```

Fallback: if LLM returns invalid JSON or Pydantic validation fails → retry with smaller model → deterministic fallback (regex patterns for common refund/delivery emails).

### 3.2 `verify_fulfillment` (verification_service.py)

```
Input: promise_id

1. Load promise (amount_paise, merchant_id, due_date, merchant_name)
2. Query bank_credits WHERE user_id=promise.user_id
   AND amount_paise = promise.amount_paise   (exact match)
   AND credited_at BETWEEN due_date-7days AND due_date+7days
3. For each candidate credit:
   a. rapidfuzz.ratio(credit.narration, promise.merchant_name) >= 85 → match
4. Results:
   - 0 matches  → no action (promise stays pending/overdue)
   - 1 match    → INSERT verification_match(is_ambiguous=false)
                  UPDATE promise.status = 'kept'
   - 2+ matches → INSERT all matches with is_ambiguous=true
                  UPDATE promise.status = 'needs_review'
                  (never auto-close ambiguous)
```

### 3.3 Escalation Ladder (escalation_service.py)

**Rung thresholds** (from config `ESCALATION_THRESHOLDS_DAYS = [7, 21, 45]`):

| Rung | Days overdue | Notice type | Action |
|---|---|---|---|
| 1 | 0–7 | `polite_nudge` | Friendly follow-up email draft |
| 2 | 8–21 | `formal_grievance` | Formal complaint draft |
| 3 | 22–45 | `nch_draft` | National Consumer Helpline complaint |
| 4 | 46+ | `consumer_commission` | Consumer Commission filing draft |

```
build_ladder(promise_id):
  1. Determine days_overdue from (today - due_date)
  2. Compute which rungs should exist based on thresholds
  3. Upsert escalation_steps for rungs not yet created
  4. Return list of EscalationStep with draft_text if already generated

generate_draft(promise_id, rung):
  1. Build draft prompt with: merchant_name, amount, due_date, exact_quote, rung
  2. LLM call → draft_text
  3. Append NOT_LEGAL_ADVICE_TEXT unconditionally
  4. UPDATE escalation_step.draft_text, draft_generated_at
```

### 3.4 Idempotency (middleware + router)

On every `POST` request:
1. Read `Idempotency-Key` header.
2. Query `idempotency_keys` by `(key, user_id)`.
3. If found and not expired → return cached `response_json` with `200` (not `201`).
4. If not found → process request → store `response_json` in table with `expires_at = now() + 24h`.
5. Implemented as a FastAPI middleware or dependency (`idempotency_dependency`).

### 3.5 Data Purge & Account Deletion

**Email body purge:** `email.body_text = NULL` immediately after `extract_promises` completes.

**Account delete (`DELETE /auth/me`):**
```
1. Revoke Gmail OAuth token via Google API (best-effort)
2. DELETE oauth_tokens WHERE user_id = ...
3. Cascade delete all user rows (FK ON DELETE CASCADE handles child tables)
4. UPDATE users SET deleted_at = now()  (soft-delete for audit)
5. Clear session cookie
```

---

## 4. LLM Router (`llm/router.py`)

### 4.1 Provider Chain

```
Groq gpt-oss-120b
  → Groq gpt-oss-20b
    → Gemini gemini-3.5-flash-lite
      → Mistral ministral-8b-latest
        → deterministic (regex fallback)
```

### 4.2 Failover Logic

```python
_semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENT)  # default 3
_cooldowns: dict[str, datetime] = {}  # provider → available_after

async def call(prompt: str, schema: type[BaseModel]) -> BaseModel:
    async with _semaphore:
        for provider in settings.LLM_PROVIDERS:
            if _cooldowns.get(provider, datetime.min) > datetime.utcnow():
                continue   # skip cooling-down provider
            try:
                raw = await _providers[provider].complete(prompt)
                result = schema.model_validate_json(raw)
                await _cache_store(prompt, raw, provider)
                return result
            except (httpx.HTTPStatusError) as e:
                if e.response.status_code in (429, 503):
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    _cooldowns[provider] = datetime.utcnow() + timedelta(seconds=retry_after)
                continue
            except (ValidationError, asyncio.TimeoutError):
                continue
        return _deterministic_fallback(prompt)  # last resort
```

### 4.3 Cache Lookup

Before calling any provider:
1. `prompt_hash = sha256(normalize(prompt))`
2. Query `llm_cache WHERE prompt_hash = ? AND expires_at > now()`
3. Cache hit → return `schema.model_validate_json(cached.response_json)`
4. Cache miss → call providers → store result

### 4.4 Prompt Injection Guard (`llm/guard.py`)

```python
def check_injection(exact_quote: str, body_text: str) -> bool:
    """
    Returns True (flagged) if exact_quote is NOT a literal substring of body_text.
    This catches cases where the LLM was tricked into fabricating a quote.
    """
    return exact_quote.strip() not in body_text
```

If flagged: `promise.needs_review_reason = "Possible prompt injection detected"`, confidence overridden to `0.0`.

---

## 5. MCP Architecture (`mcp_server.py`)

FastMCP is mounted at `/mcp` on the same FastAPI app instance. All 5 tools are **read-only** — no write, send, or mutation tools exposed.

```python
from fastmcp import FastMCP
mcp = FastMCP("Hisaab MCP Server")
app.mount("/mcp", mcp.get_asgi_app())
```

### Tool Definitions

#### `extract_promises(email_text: str) → list[PromiseCandidate]`
- Runs the full LLM extraction pipeline on supplied text.
- Returns list of `{merchant_name, amount_paise, due_date, exact_quote, confidence}`.
- Does **not** persist to DB (read-only preview tool).

#### `verify_fulfillment(promise_id: str) → VerificationResult`
- Loads promise from DB, runs verification logic against `bank_credits`.
- Returns `{match_found, credit_id, match_score, is_ambiguous}`.
- Does **not** update promise status.

#### `next_escalation_step(promise_id: str) → EscalationSuggestion`
- Computes current rung based on days overdue.
- Returns `{rung, deadline, notice_type, suggested_action, days_overdue}`.
- Does **not** generate draft or write `escalation_steps`.

#### `build_dossier(promise_id: str) → DossierSummary`
- Assembles structured JSON summary: promise details, all escalation steps, verification matches, merchant stats.
- Does **not** trigger PDF generation.
- Returns JSON suitable for LLM consumption or display.

#### `check_merchant_record(merchant_id: str) → MerchantStats`
- Returns `{merchant_name, domain, total_promises, kept_count, overdue_count, fulfillment_rate_pct, avg_resolution_days}`.

---

## 6. Auth Flow

### 6.1 Google OAuth

```
Client                     Backend                    Google
  │                           │                          │
  │  GET /api/v1/auth/google/start                       │
  │──────────────────────────▶│                          │
  │  302 → Google consent URL │                          │
  │◀──────────────────────────│                          │
  │                           │                          │
  │  [user clicks Allow]      │                          │
  │  GET /api/v1/auth/google/callback?code=...           │
  │──────────────────────────▶│                          │
  │                           │  POST /token (exchange)  │
  │                           │─────────────────────────▶│
  │                           │  access_token + refresh  │
  │                           │◀─────────────────────────│
  │                           │                          │
  │                           │  Upsert user             │
  │                           │  Encrypt + store tokens  │
  │                           │  Sign JWT session        │
  │  Set-Cookie: session=JWT  │                          │
  │◀──────────────────────────│                          │
  │  302 → /dashboard         │                          │
```

**Scope:** `openid email profile https://www.googleapis.com/auth/gmail.readonly` only.

### 6.2 Session (Signed JWT)

- **No extra DB table.** Session is a signed JWT stored in an `httpOnly; Secure; SameSite=Lax` cookie.
- Payload: `{ sub: user_id, exp: now+7d, iat: now }`.
- Signed with `SECRET_KEY` using HS256.
- `get_current_user` dependency: decode JWT → load user from DB → return `User`.
- On account delete: session cookie cleared client-side; JWT naturally expires (short TTL) server-side.

### 6.3 Demo Mode

```
POST /api/v1/auth/demo
  1. Create User(is_demo=True, email=f"demo_{uuid4()}@hisaab.demo")
  2. Load seed data (promises, merchants, bank_credits) from seed fixtures
  3. Create job rows as 'done' so UI shows realistic state
  4. Sign JWT session for the demo user
  5. Return session cookie
```

Demo users are automatically purged after 24 h (cleanup BackgroundTask on lifespan).

### 6.4 Token Encryption (`utils/encryption.py`)

```python
# AES-256-GCM
def encrypt(plaintext: str, key: bytes) -> str:
    nonce = os.urandom(12)
    cipher = AESGCM(key)
    ct = cipher.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(ciphertext: str, key: bytes) -> str:
    raw = base64.b64decode(ciphertext)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ct, None).decode()
```

`key` = `sha256(settings.SECRET_KEY.get_secret_value().encode())[:32]`

---

## 7. Error Handling & Security

### 7.1 Error Response Format

All errors use the `{ data: null, error: { code, message, details? } }` envelope:

```python
class ErrorDetail(BaseModel):
    code: str          # e.g. "GMAIL_AUTH_EXPIRED"
    message: str       # human-readable
    details: dict | None = None

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": exc.detail.model_dump()},
    )
```

**Never** return Python tracebacks in production (`ENVIRONMENT != 'dev'`).

### 7.2 Error Code Registry

| Code | HTTP | Trigger |
|---|---|---|
| `GMAIL_AUTH_EXPIRED` | 401 | OAuth token refresh fails |
| `GMAIL_SCOPE_INSUFFICIENT` | 403 | Scope missing `gmail.readonly` |
| `SYNC_IN_PROGRESS` | 409 | Duplicate sync job created |
| `LLM_UNAVAILABLE` | 503 | All providers in failover exhausted |
| `PROMISE_NOT_FOUND` | 404 | Promise ID not found for user |
| `DUPLICATE_EMAIL` | 409 | `gmail_message_id` already in DB |
| `CREDIT_UPLOAD_FAILED` | 422 | Required columns absent or CSV parse failure |
| `INVALID_IDEMPOTENCY_KEY` | 400 | Key too long or malformed |
| `PROMPT_INJECTION_DETECTED` | — | (not HTTP error; sets `needs_review_reason`) |
| `MERCHANT_NOT_FOUND` | 404 | Merchant ID not found |
| `JOB_NOT_FOUND` | 404 | Job ID not found for user |

### 7.3 Structured Logging

Every log line includes:
```python
# middleware sets request_id = uuid4() per request
logger.info("promise.extracted", extra={
    "request_id": request.state.request_id,
    "user_id": str(user.id),
    "promise_id": str(promise.id),
    "extraction_method": "llm",
})
```

Log format: JSON (structlog) in production; pretty in dev.

### 7.4 Rate Limiting (`utils/rate_limit.py`)

- Uses **slowapi** (Starlette middleware, Redis-free — in-memory or DB-backed).
- Per-user (keyed on `user.id` from session) per-endpoint.
- Defaults from config; tighter on expensive endpoints:

| Endpoint | Limit |
|---|---|
| `POST /gmail/sync` | 5/hour per user |
| `POST /credits/upload` | 10/hour per user |
| `POST /escalation/draft` | 20/hour per user |
| `GET /promises` | 120/minute per user |
| `POST /auth/demo` | 30/hour per IP |

### 7.5 Security Checklist

- **SQL injection:** ORM only; no f-strings or `.text()` with user input.
- **Input validation:** Pydantic v2 strict mode on all request bodies.
- **CORS:** Only allow frontend origin(s); credentials=true.
- **HTTPS:** Enforced in prod (`SECURE` cookie flag, `Strict-Transport-Security` header).
- **Token storage:** AES-256-GCM encrypted at rest; never logged.
- **Gmail scope:** Minimal (`gmail.readonly`); never request write scopes.
- **Prompt injection:** `guard.py` checks every extracted `exact_quote` against source body.
- **Demo isolation:** Demo users cannot trigger real Gmail sync or see real user data.
- **Idempotency expiry:** Keys auto-expire after 24 h (cleanup in lifespan).
- **LLM cache expiry:** `expires_at` enforced; stale entries not served.
