# Hisaab — Planning Assumptions

These assumptions were made where requirements were ambiguous or underspecified. They are final unless both developers agree to change them via a `contract-change` PR.

| ID | Area | Assumption | Rationale |
|---|---|---|---|
| A-01 | Session | Session uses a signed JWT stored in an `httpOnly` cookie (`session_id`), not a server-side session table | Simpler; avoids an extra DB table; 7-day TTL limits exposure |
| A-02 | Demo purge | Demo user accounts are automatically purged after 24 hours | Prevents orphaned synthetic demo data from accumulating |
| A-03 | Verification | Amount match is exact `amount_paise` (zero tolerance) | Prevents false positives; partial refunds are routed to `needs_review` |
| A-04 | Fuzzy match | `rapidfuzz.ratio` threshold is set at `85%` | Balances recall vs. precision for Indian merchant narrations |
| A-05 | Date window | `±7` calendar days around `due_date` for credit matching | Covers typical Indian banking settlement delays |
| A-06 | Email purge | Raw `email.body_text` is set to `NULL` immediately after `extract_promises` completes | Minimal data retention; keeps only `body_hash` and `exact_quote` |
| A-07 | LLM cache TTL | `llm_cache` entries expire after 24 hours (`86400` seconds) | Balances API quota savings with freshness |
| A-08 | CSV columns | Required CSV columns: `date`, `description`, `amount`, `reference_number` | Covers common Indian bank statement exports |
| A-09 | Category enum | `refund`, `delivery_credit`, `insurance`, `ticket`, `other` | Covers all major consumer promise categories in MVP |
| A-10 | Health check | `/api/v1/health` checks `database` and `llm` only (no `redis`) | Redis is explicitly excluded from the MVP architecture |
| A-11 | Timeline events | Promise `timeline` is computed from `promises`, `verification_matches`, and `escalation_steps` | Avoids an extra `timeline_events` table in MVP |
| A-12 | Escalation rungs | Escalation ladder has 4 rungs (`1`–`4`), matching `7`, `21`, `45`, `46+` day thresholds | Matches MVP specification exactly |
| A-13 | Idempotency scope | `idempotency_keys` are scoped by `(key, user_id, endpoint)` with 24 h TTL | Prevents cross-user replay and bounds table growth |
| A-14 | Partial refund | Partial amount match transitions promise to `needs_review`, never `kept` | Ambiguous or partial matches must never auto-close |
| A-15 | Demo simulator | `POST /api/v1/demo/simulate` is restricted to `is_demo = true` accounts | Prevents synthetic mutations on real user data |
| A-16 | Credit field mapping | `BankCredit` API fields `date` and `description` map from DB columns `credited_at` and `narration` | Keeps DB schema explicit while keeping API payload concise |
