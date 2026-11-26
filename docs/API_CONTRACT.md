# Hisaab API Contract

> **Version**: v1  
> **Base Path**: `/api/v1`  
> **Last Updated**: 2026-11-26

---

## Table of Contents

- [Global Conventions](#global-conventions)
- [Contract Change Policy](#contract-change-policy)
- [Error Codes Reference](#error-codes-reference)
- [Auth Group](#auth-group)
- [Gmail Group](#gmail-group)
- [Jobs Group](#jobs-group)
- [Promises Group](#promises-group)
- [Credits Group](#credits-group)
- [Verify Group](#verify-group)
- [Escalation Group](#escalation-group)
- [Dossier Group](#dossier-group)
- [Dashboard Group](#dashboard-group)
- [Merchant Group](#merchant-group)
- [Demo Group](#demo-group)
- [Health](#health)
- [Demo Story Seed Data](#demo-story-seed-data)

---

## Global Conventions

| Concern | Rule |
|---|---|
| **Base path** | `/api/v1` |
| **Serialization** | JSON, `snake_case` field names |
| **IDs** | UUID v4 strings |
| **Money** | Integer paise in fields named `amount_paise` (e.g. ₹2,499 → `249900`) |
| **Dates** | ISO 8601; `due_date` → `YYYY-MM-DD`; timestamps → UTC with `Z` suffix |
| **Pagination** | Cursor-based: `next_cursor`, `prev_cursor`, `limit` |
| **Idempotency** | `Idempotency-Key` header on all state-changing POSTs |
| **Auth** | `httpOnly` session cookie named `session_id` |
| **Content-Type** | `application/json` unless stated otherwise |

### Response Envelope

Every response (success or error) is wrapped:

```json
{
  "data": { ... },
  "error": null
}
```

On error:

```json
{
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": { ... }
  }
}
```

### Pagination Object

Returned inside `data` on list endpoints:

```json
{
  "items": [ ... ],
  "next_cursor": "opaque-cursor-string-or-null",
  "prev_cursor": "opaque-cursor-string-or-null",
  "limit": 20
}
```

---

## Contract Change Policy

1. **Additive changes only** inside `v1` — adding optional fields, new endpoints, or new enum values never requires a version bump.
2. **Breaking change** (rename, remove, type change, required-field addition, semantic change) requires:
   - A PR labelled `contract-change`
   - `contracts/openapi.yaml` updated **before** any implementation code
   - Approval from **both** developers before merge
3. A "breaking change" to a field used only in the Demo group may be waived if no external consumers exist — document the waiver in the PR.
4. Version `v2` namespace is reserved for future breaking changes.

---

## Error Codes Reference

| Code | HTTP Status | Meaning |
|---|---|---|
| `AUTH_REQUIRED` | 401 | No valid session cookie |
| `VALIDATION_ERROR` | 422 | Request body / params failed validation |
| `NOT_FOUND` | 404 | Resource does not exist |
| `RATE_LIMITED` | 429 | Too many requests |
| `LLM_UNAVAILABLE` | 503 | LLM provider down or quota exceeded |
| `GMAIL_AUTH_EXPIRED` | 401 | Gmail OAuth token expired or revoked |
| `SYNC_IN_PROGRESS` | 409 | A Gmail sync job is already running |
| `PROMISE_NOT_FOUND` | 404 | The given `promise_id` does not exist |
| `CREDIT_UPLOAD_FAILED` | 422 | CSV parse or column-mapping failure |
| `JOB_NOT_FOUND` | 404 | The given `job_id` does not exist |
| `DOSSIER_GENERATION_FAILED` | 500 | PDF generation pipeline failed |

---

## Auth Group

### [AUTH-01] GET /api/v1/auth/google/start

Initiates Google OAuth 2.0 login flow. Returns a redirect URL that the client should navigate to.

**Auth**: None required

**Request**: No body. No query parameters.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.redirect_url` | string (URL) | Google OAuth authorization URL |

**Errors**: None expected (pure URL construction)

**Success Example**:
```json
{
  "data": {
    "redirect_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&scope=email+profile&state=abc123"
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "OAuth configuration missing",
    "details": {}
  }
}
```

---

### [AUTH-02] GET /api/v1/auth/google/callback

OAuth callback handler. Exchanges the authorization code for tokens, creates or updates the user record, and sets the `session_id` cookie.

**Auth**: None required (this endpoint establishes auth)

**Request**:

| Query Param | Type | Required | Description |
|---|---|---|---|
| `code` | string | Yes | OAuth authorization code from Google |
| `state` | string | Yes | Anti-CSRF state token |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.user_id` | string (UUID) | Hisaab user ID |
| `data.email` | string | Google account email |
| `data.display_name` | string | Google display name |
| `data.created_at` | string (ISO 8601) | Account creation timestamp |

**Errors**: `VALIDATION_ERROR`

**Sets Cookie**: `session_id` (httpOnly, Secure, SameSite=Lax)

**Success Example**:
```json
{
  "data": {
    "user_id": "d4e8f012-3456-7890-abcd-ef0123456789",
    "email": "rahul@example.com",
    "display_name": "Rahul Sharma",
    "created_at": "2026-11-01T10:00:00Z"
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid or expired state token",
    "details": { "field": "state" }
  }
}
```

---

### [AUTH-03] POST /api/v1/auth/demo

Creates (or resets) a seeded demo user with pre-populated promises and credits. Sets `session_id` cookie. Idempotent per `Idempotency-Key`.

**Auth**: None required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID to prevent duplicate demo creation |

**Request**: No body required.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.user_id` | string (UUID) | Demo user ID |
| `data.email` | string | Demo email address |
| `data.display_name` | string | Demo display name |
| `data.is_demo` | boolean | Always `true` |
| `data.seed_scenario` | string | Name of seed dataset applied |

**Errors**: `RATE_LIMITED`

**Sets Cookie**: `session_id` (httpOnly, Secure, SameSite=Lax)

**Success Example**:
```json
{
  "data": {
    "user_id": "00000000-demo-0000-0000-000000000001",
    "email": "demo@hisaab.app",
    "display_name": "Demo User",
    "is_demo": true,
    "seed_scenario": "v1_standard_8_promises"
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many demo accounts created from this IP",
    "details": { "retry_after_seconds": 60 }
  }
}
```

---

### [AUTH-04] POST /api/v1/auth/logout

Destroys the server-side session and clears the `session_id` cookie.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Request**: No body.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.logged_out` | boolean | Always `true` on success |

**Errors**: `AUTH_REQUIRED`

**Clears Cookie**: `session_id`

**Success Example**:
```json
{
  "data": { "logged_out": true },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "No active session",
    "details": {}
  }
}
```

---

### [AUTH-05] GET /api/v1/auth/me

Returns the currently authenticated user's profile.

**Auth**: Required

**Request**: No parameters.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.user_id` | string (UUID) | Hisaab user ID |
| `data.email` | string | Account email |
| `data.display_name` | string | Display name |
| `data.is_demo` | boolean | Whether this is a demo account |
| `data.gmail_connected` | boolean | Whether Gmail OAuth is active |
| `data.created_at` | string (ISO 8601) | Account creation timestamp |

**Errors**: `AUTH_REQUIRED`

**Success Example**:
```json
{
  "data": {
    "user_id": "d4e8f012-3456-7890-abcd-ef0123456789",
    "email": "rahul@example.com",
    "display_name": "Rahul Sharma",
    "is_demo": false,
    "gmail_connected": true,
    "created_at": "2026-11-01T10:00:00Z"
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "AUTH_REQUIRED",
    "message": "Session expired or not found",
    "details": {}
  }
}
```

---

### [AUTH-06] DELETE /api/v1/auth/me

Revokes Gmail OAuth token (best-effort), cascade-deletes all user data, soft-deletes the user record, and clears the `session_id` cookie.

**Auth**: Required

**Request**: No body.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.deleted` | boolean | Always `true` on success |

**Errors**: `AUTH_REQUIRED`

**Clears Cookie**: `session_id`

**Success Example**:
```json
{
  "data": { "deleted": true },
  "error": null
}
```

---

## Gmail Group

### [GMAIL-01] POST /api/v1/gmail/connect

Initiates the Gmail OAuth flow for `gmail.readonly` scope. Returns a redirect URL for the client to navigate to.

**Auth**: Required (Hisaab session must exist)

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Request**: No body.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.redirect_url` | string (URL) | Gmail OAuth authorization URL |

**Errors**: `AUTH_REQUIRED`

**Success Example**:
```json
{
  "data": {
    "redirect_url": "https://accounts.google.com/o/oauth2/v2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly&..."
  },
  "error": null
}
```

---

### [GMAIL-02] POST /api/v1/gmail/disconnect

Revokes the Gmail OAuth token and purges all raw email data for this user. Keeps extracted promise data.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Request**: No body.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.disconnected` | boolean | Always `true` on success |
| `data.emails_purged` | integer | Count of raw email records deleted |

**Errors**: `AUTH_REQUIRED`

**Success Example**:
```json
{
  "data": {
    "disconnected": true,
    "emails_purged": 1247
  },
  "error": null
}
```

---

### [GMAIL-03] POST /api/v1/gmail/sync

Enqueues a background Gmail sync job. Returns immediately with a `job_id`. Idempotent — if a sync is already running, returns the existing job's ID with status `409`.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Request**:

| Field | Type | Required | Description |
|---|---|---|---|
| `full_resync` | boolean | No | If `true`, re-processes all emails; default `false` |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.job_id` | string (UUID) | Background job identifier |
| `data.status` | string | `"queued"` or `"running"` |
| `data.enqueued_at` | string (ISO 8601) | When the job was enqueued |

**Errors**: `AUTH_REQUIRED`, `GMAIL_AUTH_EXPIRED`, `SYNC_IN_PROGRESS`

**Success Example**:
```json
{
  "data": {
    "job_id": "aabb1234-5678-90ab-cdef-012345678901",
    "status": "queued",
    "enqueued_at": "2026-11-26T07:00:00Z"
  },
  "error": null
}
```

**Error Example** (sync already running):
```json
{
  "data": null,
  "error": {
    "code": "SYNC_IN_PROGRESS",
    "message": "A Gmail sync is already in progress",
    "details": { "job_id": "aabb1234-5678-90ab-cdef-012345678901" }
  }
}
```

---

### [GMAIL-04] GET /api/v1/gmail/status

Returns current Gmail connection status and sync information.

**Auth**: Required

**Request**: No parameters.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.connected` | boolean | Whether Gmail OAuth is active |
| `data.email` | string \| null | Connected Gmail address |
| `data.last_synced_at` | string (ISO 8601) \| null | Timestamp of last completed sync |
| `data.sync_status` | string | `"idle"`, `"queued"`, or `"running"` |
| `data.active_job_id` | string (UUID) \| null | Running job ID if any |
| `data.emails_processed` | integer | Total emails processed to date |

**Errors**: `AUTH_REQUIRED`

**Success Example**:
```json
{
  "data": {
    "connected": true,
    "email": "rahul@example.com",
    "last_synced_at": "2026-11-25T23:00:00Z",
    "sync_status": "idle",
    "active_job_id": null,
    "emails_processed": 1247
  },
  "error": null
}
```

---

## Jobs Group

### [JOBS-01] GET /api/v1/jobs/{job_id}

Polls the status of any background job (sync, CSV upload, dossier generation).

**Auth**: Required

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `job_id` | string (UUID) | Job identifier |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.job_id` | string (UUID) | Job ID |
| `data.type` | string | `"gmail_sync"`, `"credit_upload"`, or `"dossier_generation"` |
| `data.status` | string | `"queued"`, `"running"`, `"completed"`, or `"failed"` |
| `data.progress_pct` | integer \| null | 0–100 if available |
| `data.created_at` | string (ISO 8601) | Job creation time |
| `data.completed_at` | string (ISO 8601) \| null | Completion time |
| `data.result` | object \| null | Job-type-specific result payload |
| `data.error_message` | string \| null | Human-readable error if status is `"failed"` |

**Errors**: `AUTH_REQUIRED`, `JOB_NOT_FOUND`

**Success Example** (completed sync):
```json
{
  "data": {
    "job_id": "aabb1234-5678-90ab-cdef-012345678901",
    "type": "gmail_sync",
    "status": "completed",
    "progress_pct": 100,
    "created_at": "2026-11-26T07:00:00Z",
    "completed_at": "2026-11-26T07:04:30Z",
    "result": {
      "emails_scanned": 1247,
      "promises_extracted": 3,
      "promises_updated": 1
    },
    "error_message": null
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "No job found with the given ID",
    "details": { "job_id": "aabb1234-0000-0000-0000-000000000000" }
  }
}
```

---

## Promises Group

### [PROMISES-01] GET /api/v1/promises

Lists all promises for the authenticated user. Supports cursor-based pagination and filtering.

**Auth**: Required

**Query Parameters**:

| Param | Type | Required | Description |
|---|---|---|---|
| `status` | string | No | Filter: `pending`, `kept`, `overdue`, `needs_review`, `dismissed` |
| `category` | string | No | Filter: `refund`, `delivery_credit`, `insurance`, `ticket`, `other` |
| `merchant_id` | string (UUID) | No | Filter by merchant |
| `date_from` | string (YYYY-MM-DD) | No | Promises with `due_date` ≥ this date |
| `date_to` | string (YYYY-MM-DD) | No | Promises with `due_date` ≤ this date |
| `limit` | integer | No | Page size; default 20, max 100 |
| `cursor` | string | No | Opaque cursor from previous response |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.items` | array | Array of promise summary objects |
| `data.items[].promise_id` | string (UUID) | Promise ID |
| `data.items[].merchant_name` | string | Merchant name |
| `data.items[].merchant_id` | string (UUID) | Merchant ID |
| `data.items[].category` | string | Promise category |
| `data.items[].amount_paise` | integer | Promised amount |
| `data.items[].status` | string | Current status |
| `data.items[].due_date` | string (YYYY-MM-DD) | Expected fulfillment date |
| `data.items[].created_at` | string (ISO 8601) | Extraction timestamp |
| `data.next_cursor` | string \| null | Cursor for next page |
| `data.prev_cursor` | string \| null | Cursor for previous page |
| `data.limit` | integer | Applied limit |

**Errors**: `AUTH_REQUIRED`, `VALIDATION_ERROR`

**Success Example**:
```json
{
  "data": {
    "items": [
      {
        "promise_id": "11111111-0001-0000-0000-000000000001",
        "merchant_name": "Flipkart",
        "merchant_id": "aaaaaaaa-0001-0000-0000-000000000001",
        "category": "refund",
        "amount_paise": 249900,
        "status": "kept",
        "due_date": "2026-11-15",
        "created_at": "2026-11-01T12:00:00Z"
      },
      {
        "promise_id": "11111111-0002-0000-0000-000000000002",
        "merchant_name": "HDFC Insurance",
        "merchant_id": "aaaaaaaa-0002-0000-0000-000000000002",
        "category": "insurance",
        "amount_paise": 1500000,
        "status": "overdue",
        "due_date": "2026-11-10",
        "created_at": "2026-10-15T09:00:00Z"
      }
    ],
    "next_cursor": "eyJpZCI6IjExMTExMTExLTAwMDMifQ==",
    "prev_cursor": null,
    "limit": 20
  },
  "error": null
}
```

---

### [PROMISES-02] GET /api/v1/promises/{promise_id}

Retrieves full detail for a single promise, including its timeline of events.

**Auth**: Required

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise ID |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.promise_id` | string (UUID) | Promise ID |
| `data.merchant_name` | string | Merchant name |
| `data.merchant_id` | string (UUID) | Merchant ID |
| `data.category` | string | Category |
| `data.amount_paise` | integer | Promised amount |
| `data.received_amount_paise` | integer \| null | Amount actually received |
| `data.status` | string | Current status |
| `data.due_date` | string (YYYY-MM-DD) | Expected date |
| `data.source_email_id` | string \| null | Gmail message ID |
| `data.source_email_subject` | string \| null | Email subject |
| `data.user_note` | string \| null | User-added note |
| `data.escalation_rung` | integer \| null | Current escalation level (1–4) |
| `data.exact_quote` | string | Literal substring extracted from email |
| `data.confidence` | number | LLM extraction confidence (0.0–1.0) |
| `data.extraction_method` | string | `"llm"` or `"deterministic"` |
| `data.needs_review_reason` | string \| null | Reason flagged for review, if any |
| `data.created_at` | string (ISO 8601) | Extraction time |
| `data.updated_at` | string (ISO 8601) | Last update time |
| `data.timeline` | array | Array of timeline events |
| `data.timeline[].event_id` | string (UUID) | Event ID |
| `data.timeline[].type` | string | Event type |
| `data.timeline[].description` | string | Human-readable description |
| `data.timeline[].occurred_at` | string (ISO 8601) | Event timestamp |
| `data.timeline[].metadata` | object \| null | Extra event data |

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`

**Success Example**:
```json
{
  "data": {
    "promise_id": "11111111-0002-0000-0000-000000000002",
    "merchant_name": "HDFC Insurance",
    "merchant_id": "aaaaaaaa-0002-0000-0000-000000000002",
    "category": "insurance",
    "amount_paise": 1500000,
    "received_amount_paise": null,
    "status": "overdue",
    "due_date": "2026-11-10",
    "source_email_id": "msg_hdfc_001",
    "source_email_subject": "Your claim #CLM-2026-4521 has been approved",
    "user_note": "Called helpline on Nov 12, they said processing",
    "escalation_rung": 2,
    "exact_quote": "Your claim #CLM-2026-4521 of Rs. 15,000 has been approved and will be credited by Nov 10, 2026.",
    "confidence": 0.97,
    "extraction_method": "llm",
    "needs_review_reason": null,
    "created_at": "2026-10-15T09:00:00Z",
    "updated_at": "2026-11-20T14:30:00Z",
    "timeline": [
      {
        "event_id": "evt-0001-0000-0000-0000-000000000001",
        "type": "promise_extracted",
        "description": "Promise extracted from email",
        "occurred_at": "2026-10-15T09:00:00Z",
        "metadata": { "confidence_score": 0.97 }
      },
      {
        "event_id": "evt-0001-0000-0000-0000-000000000002",
        "type": "overdue_detected",
        "description": "Due date passed without matching bank credit",
        "occurred_at": "2026-11-11T00:01:00Z",
        "metadata": null
      },
      {
        "event_id": "evt-0001-0000-0000-0000-000000000003",
        "type": "escalation_advanced",
        "description": "Escalation advanced to rung 2",
        "occurred_at": "2026-11-15T08:00:00Z",
        "metadata": { "rung": 2 }
      }
    ]
  },
  "error": null
}
```

---

### [PROMISES-03] PATCH /api/v1/promises/{promise_id}

Updates a promise's status (e.g., dismiss) or user note.

**Auth**: Required

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise ID |

**Request Body**:

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | No | New status: only `"dismissed"` is user-settable |
| `user_note` | string | No | Free-text note; max 2000 chars |

**Response**: Updated promise summary (same as list item shape).

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`, `VALIDATION_ERROR`

**Success Example**:
```json
{
  "data": {
    "promise_id": "11111111-0008-0000-0000-000000000008",
    "merchant_name": "Swiggy",
    "merchant_id": "aaaaaaaa-0008-0000-0000-000000000008",
    "category": "other",
    "amount_paise": 50000,
    "status": "dismissed",
    "due_date": "2026-11-20",
    "created_at": "2026-11-05T10:00:00Z"
  },
  "error": null
}
```

---

## Credits Group

### [CREDITS-01] POST /api/v1/credits/upload

Accepts a CSV file (multipart/form-data) of bank credit transactions. Enqueues a background processing job that attempts to match credits to open promises.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Request**: `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | Yes | CSV file; max 10 MB |
| `bank_name` | string | Yes | Bank identifier (e.g. `"HDFC"`, `"SBI"`, `"ICICI"`) |
| `account_last4` | string | No | Last 4 digits of account for disambiguation |

**Expected CSV Columns**: `date`, `description`, `amount`, `reference_number`

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.job_id` | string (UUID) | Processing job ID |
| `data.rows_detected` | integer | Number of CSV rows found |
| `data.status` | string | Always `"queued"` |

**Errors**: `AUTH_REQUIRED`, `VALIDATION_ERROR`, `CREDIT_UPLOAD_FAILED`

**Success Example**:
```json
{
  "data": {
    "job_id": "ccdd5678-9012-34ef-ab56-78901234cdef",
    "rows_detected": 42,
    "status": "queued"
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "CREDIT_UPLOAD_FAILED",
    "message": "CSV is missing required column: amount",
    "details": { "missing_columns": ["amount"] }
  }
}
```

---

### [CREDITS-02] GET /api/v1/credits

Lists bank credit records for the authenticated user. Cursor-paginated.

**Auth**: Required

**Query Parameters**:

| Param | Type | Required | Description |
|---|---|---|---|
| `limit` | integer | No | Page size; default 20, max 100 |
| `cursor` | string | No | Opaque cursor |
| `matched` | boolean | No | Filter by match status |
| `date_from` | string (YYYY-MM-DD) | No | Credits on or after this date |
| `date_to` | string (YYYY-MM-DD) | No | Credits on or before this date |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.items[].credit_id` | string (UUID) | Credit record ID |
| `data.items[].date` | string (YYYY-MM-DD) | Transaction date |
| `data.items[].description` | string | Bank transaction description |
| `data.items[].amount_paise` | integer | Credit amount |
| `data.items[].reference_number` | string \| null | Bank reference |
| `data.items[].matched_promise_id` | string (UUID) \| null | Matched promise, if any |
| `data.items[].bank_name` | string | Bank identifier |

**Errors**: `AUTH_REQUIRED`

**Success Example**:
```json
{
  "data": {
    "items": [
      {
        "credit_id": "cccc0001-0000-0000-0000-000000000001",
        "date": "2026-11-14",
        "description": "FLIPKART REFUND REF FKT2026112201",
        "amount_paise": 249900,
        "reference_number": "FKT2026112201",
        "matched_promise_id": "11111111-0001-0000-0000-000000000001",
        "bank_name": "HDFC"
      }
    ],
    "next_cursor": null,
    "prev_cursor": null,
    "limit": 20
  },
  "error": null
}
```

---

## Verify Group

### [VERIFY-01] POST /api/v1/verify/{promise_id}

Triggers a re-verification pass for a promise against currently-uploaded bank credits. Pure deterministic code — no LLM involved.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise to verify |

**Request**: No body.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.promise_id` | string (UUID) | Promise ID |
| `data.previous_status` | string | Status before verification |
| `data.new_status` | string | Status after verification |
| `data.matched_credit_id` | string (UUID) \| null | Matching credit found, if any |
| `data.amount_paise_expected` | integer | Promised amount |
| `data.amount_paise_received` | integer \| null | Received amount (if matched) |
| `data.verified_at` | string (ISO 8601) | Verification timestamp |

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`

**Success Example**:
```json
{
  "data": {
    "promise_id": "11111111-0005-0000-0000-000000000005",
    "previous_status": "pending",
    "new_status": "needs_review",
    "matched_credit_id": "cccc0005-0000-0000-0000-000000000005",
    "amount_paise_expected": 320000,
    "amount_paise_received": 290000,
    "verified_at": "2026-11-26T07:10:00Z"
  },
  "error": null
}
```

---

## Escalation Group

### [ESCALATION-01] GET /api/v1/escalation/{promise_id}/next-step

Returns the deterministic next escalation rung and computed deadline, with no LLM involvement.

**Auth**: Required

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise ID |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.promise_id` | string (UUID) | Promise ID |
| `data.current_rung` | integer \| null | Current escalation level |
| `data.next_rung` | integer | Recommended next level (1–4) |
| `data.rung_name` | string | Human label for next rung |
| `data.rung_description` | string | What action this rung entails |
| `data.deadline_date` | string (YYYY-MM-DD) | When to act by |
| `data.days_until_deadline` | integer | Days from today |
| `data.legal_forum` | string \| null | Applicable forum (e.g. `"Consumer Court"`) |

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`

**Success Example**:
```json
{
  "data": {
    "promise_id": "11111111-0002-0000-0000-000000000002",
    "current_rung": 2,
    "next_rung": 3,
    "rung_name": "Formal Written Complaint",
    "rung_description": "Send a formal complaint letter via registered post to HDFC Insurance grievance officer",
    "deadline_date": "2026-12-10",
    "days_until_deadline": 14,
    "legal_forum": "Insurance Ombudsman"
  },
  "error": null
}
```

---

### [ESCALATION-02] POST /api/v1/escalation/{promise_id}/draft

Calls the LLM to generate a draft escalation message (email/letter). Always includes a not-legal-advice notice in the response.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise ID |

**Request Body**:

| Field | Type | Required | Description |
|---|---|---|---|
| `rung` | integer | Yes | Target escalation rung (1–4) |
| `tone` | string | No | `"firm"` (default) or `"polite"` |
| `include_legal_references` | boolean | No | Whether to cite consumer law sections |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.draft_text` | string | Generated draft message |
| `data.rung` | integer | Escalation rung this applies to |
| `data.not_legal_advice_notice` | string | Mandatory disclaimer |
| `data.generated_at` | string (ISO 8601) | Generation timestamp |
| `data.model_used` | string | LLM model identifier |

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`, `LLM_UNAVAILABLE`, `VALIDATION_ERROR`

**Success Example**:
```json
{
  "data": {
    "draft_text": "Subject: Formal Complaint Regarding Pending Insurance Claim #CLM-2026-4521\n\nDear HDFC Insurance Grievance Officer,\n\nI am writing to formally escalate my claim...",
    "rung": 3,
    "not_legal_advice_notice": "This draft is generated by AI for reference only. It does not constitute legal advice. Please consult a qualified legal professional for advice specific to your situation.",
    "generated_at": "2026-11-26T07:15:00Z",
    "model_used": "gemini-2.0-flash"
  },
  "error": null
}
```

**Error Example**:
```json
{
  "data": null,
  "error": {
    "code": "LLM_UNAVAILABLE",
    "message": "LLM service is temporarily unavailable",
    "details": { "retry_after_seconds": 30 }
  }
}
```

---

## Dossier Group

### [DOSSIER-01] POST /api/v1/dossier/{promise_id}/generate

Enqueues a PDF dossier generation job. The dossier compiles the promise, timeline, escalation history, and relevant emails into a printable document.

**Auth**: Required

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise ID |

**Request**: No body.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.job_id` | string (UUID) | PDF generation job ID |
| `data.status` | string | Always `"queued"` |
| `data.enqueued_at` | string (ISO 8601) | Enqueue timestamp |

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`

**Success Example**:
```json
{
  "data": {
    "job_id": "ddee9012-3456-78ab-cdef-901234567890",
    "status": "queued",
    "enqueued_at": "2026-11-26T07:20:00Z"
  },
  "error": null
}
```

---

### [DOSSIER-02] GET /api/v1/dossier/{promise_id}/download

Streams the generated PDF bytes. The job must be in `completed` status.

**Auth**: Required

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `promise_id` | string (UUID) | Promise ID |

**Response**: Binary PDF stream

| Header | Value |
|---|---|
| `Content-Type` | `application/pdf` |
| `Content-Disposition` | `attachment; filename="hisaab-dossier-{promise_id}.pdf"` |

**Errors**: `AUTH_REQUIRED`, `PROMISE_NOT_FOUND`, `DOSSIER_GENERATION_FAILED`

**Error Example** (PDF not ready):
```json
{
  "data": null,
  "error": {
    "code": "DOSSIER_GENERATION_FAILED",
    "message": "Dossier has not been generated yet. Please enqueue generation first.",
    "details": { "promise_id": "11111111-0002-0000-0000-000000000002" }
  }
}
```

---

## Dashboard Group

### [DASHBOARD-01] GET /api/v1/dashboard/summary

Returns aggregated statistics for the authenticated user's promises.

**Auth**: Required

**Request**: No parameters.

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.total_owed_paise` | integer | Sum of all non-dismissed, non-kept amounts |
| `data.total_overdue_paise` | integer | Sum of overdue promise amounts |
| `data.total_kept_paise` | integer | Sum of kept promise amounts |
| `data.counts.total` | integer | All promises |
| `data.counts.pending` | integer | Pending promises |
| `data.counts.kept` | integer | Kept promises |
| `data.counts.overdue` | integer | Overdue promises |
| `data.counts.needs_review` | integer | Needs-review promises |
| `data.counts.dismissed` | integer | Dismissed promises |
| `data.computed_at` | string (ISO 8601) | When this snapshot was computed |

**Errors**: `AUTH_REQUIRED`

**Success Example** (demo story data):
```json
{
  "data": {
    "total_owed_paise": 2069900,
    "total_overdue_paise": 2150000,
    "total_kept_paise": 374800,
    "counts": {
      "total": 8,
      "pending": 1,
      "kept": 2,
      "overdue": 2,
      "needs_review": 2,
      "dismissed": 1
    },
    "computed_at": "2026-11-26T07:00:00Z"
  },
  "error": null
}
```

---

## Merchant Group

### [MERCHANT-01] GET /api/v1/merchants/{merchant_id}/record

Returns promise-keeping statistics for a specific merchant.

**Auth**: Required

**Path Parameters**:

| Param | Type | Description |
|---|---|---|
| `merchant_id` | string (UUID) | Merchant ID |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.merchant_id` | string (UUID) | Merchant ID |
| `data.merchant_name` | string | Merchant name |
| `data.total_promises` | integer | All promises from this merchant |
| `data.kept_count` | integer | Kept promises |
| `data.overdue_count` | integer | Overdue promises |
| `data.dismissed_count` | integer | Dismissed promises |
| `data.average_resolution_days` | number \| null | Avg days from promise to fulfillment |
| `data.keep_rate_pct` | number | Percentage of non-dismissed kept |

**Errors**: `AUTH_REQUIRED`, `NOT_FOUND`

**Success Example**:
```json
{
  "data": {
    "merchant_id": "aaaaaaaa-0001-0000-0000-000000000001",
    "merchant_name": "Flipkart",
    "total_promises": 1,
    "kept_count": 1,
    "overdue_count": 0,
    "dismissed_count": 0,
    "average_resolution_days": 13,
    "keep_rate_pct": 100.0
  },
  "error": null
}
```

---

## Demo Group

### [DEMO-01] POST /api/v1/demo/simulate

Simulates a scenario mutation on the demo dataset. Only works for demo accounts (`is_demo: true`).

**Auth**: Required (demo session)

**Headers**:

| Header | Required | Description |
|---|---|---|
| `Idempotency-Key` | Yes | UUID |

**Request Body**:

| Field | Type | Required | Description |
|---|---|---|---|
| `scenario` | string | Yes | One of: `refund_arrives`, `refund_delayed`, `fake_promise`, `duplicate_charge` |
| `promise_id` | string (UUID) | No | Target promise; auto-selected if omitted |

**Scenario Descriptions**:

| Scenario | Effect |
|---|---|
| `refund_arrives` | Marks a pending/overdue promise as kept; injects matching bank credit |
| `refund_delayed` | Extends due_date and adds timeline event |
| `fake_promise` | Injects a promise with `needs_review` + prompt-injection flag in metadata |
| `duplicate_charge` | Injects a duplicate-charge promise, auto-dismisses after 2s |

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.scenario` | string | Scenario applied |
| `data.affected_promise_id` | string (UUID) | Promise that was mutated |
| `data.description` | string | Human summary of changes made |
| `data.simulated_at` | string (ISO 8601) | Simulation timestamp |

**Errors**: `AUTH_REQUIRED`, `VALIDATION_ERROR`, `PROMISE_NOT_FOUND`

**Success Example**:
```json
{
  "data": {
    "scenario": "refund_arrives",
    "affected_promise_id": "11111111-0004-0000-0000-000000000004",
    "description": "Zomato delivery credit of ₹149 marked as received; bank credit injected",
    "simulated_at": "2026-11-26T07:30:00Z"
  },
  "error": null
}
```

---

## Health

### [HEALTH-01] GET /api/v1/health

Liveness and readiness check. No auth required.

**Auth**: None

**Response**:

| Field | Type | Description |
|---|---|---|
| `data.status` | string | `"ok"` or `"degraded"` |
| `data.version` | string | API version string |
| `data.checks.database` | string | `"ok"` or `"error"` |
| `data.checks.llm` | string | `"ok"` or `"degraded"` or `"error"` |
| `data.uptime_seconds` | integer | Process uptime |

**Success Example**:
```json
{
  "data": {
    "status": "ok",
    "version": "1.0.0",
    "checks": {
      "database": "ok",
      "llm": "ok"
    },
    "uptime_seconds": 86400
  },
  "error": null
}
```

---

## Demo Story Seed Data

The following 8 promises are pre-loaded for demo accounts (`POST /api/v1/auth/demo`):

| # | Merchant | Amount | Status | Notes |
|---|---|---|---|---|
| 1 | Flipkart | ₹2,499 (`249900` paise) | `kept` | Bank credit matched (REF FKT2026112201) |
| 2 | HDFC Insurance | ₹15,000 (`1500000` paise) | `overdue` | Rung 2 escalation; due_date 2026-11-10 |
| 3 | Amazon | ₹899 (`89900` paise) | `kept` | Return processed, credit received |
| 4 | Zomato | ₹149 (`14900` paise) | `pending` | Delivery credit promised, 7-day window |
| 5 | IRCTC | ₹3,200 (`320000` paise) | `needs_review` | Received ₹2,900; ₹300 mismatch flagged |
| 6 | BookMyShow | ₹650 (`65000` paise) | `overdue` | Rung 1; cancellation refund not received |
| 7 | (Injected) | ₹99,999 (`9999900` paise) | `needs_review` | Prompt injection attempt flagged in metadata |
| 8 | Swiggy | ₹500 (`50000` paise) | `dismissed` | Duplicate charge; user dismissed |

Scenario simulations (`POST /api/v1/demo/simulate`) operate on this dataset.
