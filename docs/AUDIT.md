# Hisaab Planning — Consistency Audit

Audit performed: 2026-11-26

This audit cross-checks every endpoint, field, error code, and database column across:
- [API_CONTRACT.md](file:///D:/Hisaab/docs/API_CONTRACT.md)
- [openapi.yaml](file:///D:/Hisaab/contracts/openapi.yaml)
- [FRONTEND.md](file:///D:/Hisaab/docs/FRONTEND.md)
- [BACKEND.md](file:///D:/Hisaab/docs/BACKEND.md)

---

## Summary

| Status | Count |
|---|---|
| FIXED (reconciled across docs and `openapi.yaml`) | 10 |
| OPEN ITEM (remaining) | 0 |
| CLEAN CHECKS (verified consistent) | 12 |

---

## Issues Found and Fixed

### [AUDIT-001] `redis` check in `/api/v1/health` — FIXED
- **Mismatch**: `HealthStatus` in `openapi.yaml` and `API_CONTRACT.md` (`HEALTH-01`) included `checks.redis`, whereas `BACKEND.md` and `PROJECT_PLAN.md` lock in **no Redis** (BackgroundTasks + DB `jobs` table, in-memory `slowapi`).
- **Fix Applied**: Removed `redis` from `HealthStatus` in `openapi.yaml` and `[HEALTH-01]` in `API_CONTRACT.md`. Remaining health checks: `database`, `llm`.

### [AUDIT-002] `GMAIL_TOKEN_EXPIRED` vs `GMAIL_AUTH_EXPIRED` — FIXED
- **Mismatch**: `API_CONTRACT.md` and `openapi.yaml` used `GMAIL_AUTH_EXPIRED`, while `BACKEND.md` and `FRONTEND.md` used `GMAIL_TOKEN_EXPIRED`.
- **Fix Applied**: Standardized on `GMAIL_AUTH_EXPIRED` in `BACKEND.md` and `FRONTEND.md`.

### [AUDIT-003] `CSV_WRONG_COLUMNS` vs `CREDIT_UPLOAD_FAILED` — FIXED
- **Mismatch**: `API_CONTRACT.md` and `openapi.yaml` used `CREDIT_UPLOAD_FAILED`, while `BACKEND.md` and `FRONTEND.md` used `CSV_WRONG_COLUMNS`.
- **Fix Applied**: Standardized on `CREDIT_UPLOAD_FAILED` in `BACKEND.md` and `FRONTEND.md`.

### [AUDIT-004] Job status enum (`pending`/`done` vs `queued`/`completed`) — FIXED
- **Mismatch**: `BACKEND.md` `jobs` table used `pending`, `running`, `done`, `failed`, whereas `API_CONTRACT.md` and `openapi.yaml` expose `queued`, `running`, `completed`, `failed`.
- **Fix Applied**: Documented explicit serializer mapping in `BACKEND.md` (`pending` → `queued`, `done` → `completed`).

### [AUDIT-005] `/bank-credits/*` vs `/credits/*` path prefix — FIXED
- **Mismatch**: `BACKEND.md` and `FRONTEND.md` referenced `/bank-credits/upload-csv`, whereas `API_CONTRACT.md` and `openapi.yaml` define `POST /api/v1/credits/upload` (`CREDITS-01`) and `GET /api/v1/credits` (`CREDITS-02`).
- **Fix Applied**: Updated `BACKEND.md` and `FRONTEND.md` to use `/credits/upload` and `/credits`.

### [AUDIT-006] `DELETE /api/v1/auth/me` missing from contract — FIXED
- **Mismatch**: `BACKEND.md` and `FRONTEND.md` (Settings page account deletion) required `DELETE /api/v1/auth/me`, which was absent from `API_CONTRACT.md` and `openapi.yaml`.
- **Fix Applied**: Added `[AUTH-06] DELETE /api/v1/auth/me` (`authDeleteMe`) to both `API_CONTRACT.md` and `openapi.yaml`.

### [AUDIT-007] `exact_quote`, `confidence`, `extraction_method`, `needs_review_reason` missing from `PromiseDetail` — FIXED
- **Mismatch**: `BACKEND.md` `promises` table stores `exact_quote`, `confidence`, `extraction_method`, and `needs_review_reason`, and `FRONTEND.md` (`PromiseMetaCard`, `ConfidenceMeter`, `PromptInjectionFlag`) renders them, but `PromiseDetail` in `API_CONTRACT.md` and `openapi.yaml` omitted them.
- **Fix Applied**: Added all four fields to `PromiseDetail` in `openapi.yaml` and `[PROMISES-02]` in `API_CONTRACT.md`.

### [AUDIT-008] Escalation rung max `5` vs `4` — FIXED
- **Mismatch**: `BACKEND.md` defines 4 escalation rungs (`1`–`4`), while `openapi.yaml` and `API_CONTRACT.md` had `maximum: 5` / `(1–5)`.
- **Fix Applied**: Updated `escalation_rung`, `next_rung`, and `rung` bounds to `1–4` in `openapi.yaml` and `API_CONTRACT.md`.

### [AUDIT-009] `DELETE /auth/gmail` vs `POST /api/v1/gmail/disconnect` — FIXED
- **Mismatch**: `FRONTEND.md` `GmailConnectionCard` referenced `DELETE /auth/gmail` instead of `[GMAIL-02] POST /api/v1/gmail/disconnect`.
- **Fix Applied**: Updated `FRONTEND.md` to reference `POST /api/v1/gmail/disconnect` (`GMAIL-02`).

### [AUDIT-010] `/demo/simulate/email` & `/demo/simulate/credit` vs `POST /api/v1/demo/simulate` — FIXED
- **Mismatch**: `FRONTEND.md` referenced split endpoints `/demo/simulate/email` and `/demo/simulate/credit`, whereas the contract defines a single unified endpoint `[DEMO-01] POST /api/v1/demo/simulate`.
- **Fix Applied**: Updated `FRONTEND.md` to reference `POST /api/v1/demo/simulate` (`DEMO-01`).

---

## Clean Checks

1. All 24 endpoints in `API_CONTRACT.md` match `contracts/openapi.yaml` paths, methods, and operation IDs.
2. All 8 demo story promises (IDs, amounts in paise, statuses, merchants) match between `API_CONTRACT.md` and `openapi.yaml`.
3. Response envelope `{ data, error }` with `{ code, message, details }` is consistent across all docs.
4. Money fields use integer `amount_paise` everywhere.
5. IDs are UUID strings; dates are ISO 8601 (`YYYY-MM-DD` for `due_date`, UTC `Z` for timestamps).
6. Cursor pagination (`items`, `next_cursor`, `prev_cursor`, `limit`) is consistent across list endpoints.
7. `Idempotency-Key` header is required on all state-changing `POST` endpoints.
8. LLM failover chain order (`Groq gpt-oss-120b` → `Groq gpt-oss-20b` → `Gemini gemini-3.5-flash-lite` → `Mistral ministral-8b-latest` → deterministic fallback) is consistent across `PROJECT_PLAN.md` and `BACKEND.md`.
9. Escalation rung thresholds (`7`, `21`, `45` days) and `not_legal_advice_notice` requirement are consistent.
10. MCP server (`/mcp` mount, 5 read-only tools, no send tool) is consistent across `PROJECT_PLAN.md` and `BACKEND.md`.
11. Database column types and foreign keys in `BACKEND.md` cover all API fields in `API_CONTRACT.md` and `openapi.yaml`.
12. `DEVOPS_AND_SETUP.md`, `EXECUTION_GUIDE.md`, and `PROGRESS.md` align with the monorepo layout and contract-first workflow.

---

## Audit Conclusion

**CLEAN.** All 10 cross-document mismatches identified during the audit have been resolved directly in `contracts/openapi.yaml`, `docs/API_CONTRACT.md`, `docs/FRONTEND.md`, and `docs/BACKEND.md`. The planning artifacts are consistent and ready for Phase 1 implementation.
