# Hisaab_Track_1
MCP-powered agent that tracks promises companies make to you (refunds, claims, deliveries), verifies from independent proof whether they were kept, and builds your escalation case when they weren't. Drafts only, never sends.

# Hisaab: The Promise-Keeping Agent

> *Everyone made you a promise. Hisaab makes sure it's kept.*

Built for **WHACKiest 2026** (Track: *Make MCP Matter: Less Magic, More Utility*).

Hisaab is an MCP-powered agent that reads the promises companies make to you
("refund in 10 working days", "claim settled in 30 days"), checks independent
proof of whether each was kept, and prepares your next escalation step when it
wasn't.

## The problem

Reminder apps track tasks *you* enter. Nobody tracks what *others* promised *you*.
Promises sit buried in emails and SMS, and chasing them costs more effort than
most people can spare, so many go unclaimed.

## What Hisaab does

- **Promise Extractor:** captures who promised what, the ₹ amount, the due date, and
  the exact source sentence as evidence.
- **Independent Verification:** matches bank/UPI credit alerts (not the model's
  opinion) to mark each promise **Kept / Pending / Broken**.
- **Escalation Ladder:** deadline logic drafts the next step: nudge, then
  grievance officer, then consumer helpline complaint, then consumer commission.
- **Evidence Dossier:** timeline, order IDs and proof, exportable as PDF.
- **"Owed to You" dashboard:** total ₹ owed and overdue.
- **Promise-Keeping Index:** merchant reliability, queryable via MCP
  (prototype uses seeded data).

## Safe by design

- Read-only mailbox access.
- **No send tool exists.** Every message is a draft the user reviews and sends.
- Email text is treated as untrusted data; output is schema-constrained.
- Verification and deadline logic are plain code, not LLM judgments.

## Architecture

    Claude (MCP client)
          │
    Promise MCP Server (FastMCP)
    extract · verify · escalate · dossier · merchant record
       │            │             │
    Gmail MCP   Bank alerts/CSV   Drive MCP
          └──► State engine (SQLite) ◄──┘
                      │
        React dashboard → Draft + PDF → User sends

## MCP tools

| Tool | Purpose |
|---|---|
| `extract_promises` | Structured promises with source quote and confidence |
| `verify_fulfillment` | Match bank credits to promises (amount, merchant, date window) |
| `next_escalation_step` | Deadline and grace-period logic → next rung |
| `build_dossier` | Generate the PDF evidence file |
| `check_merchant_record` | Look up a merchant's promise-keeping record |

## Tech stack

Python · FastMCP · FastAPI · Pydantic · SQLite · React · Tailwind · ReportLab ·
Gmail & Drive APIs · Claude API

## Status

Hackathon MVP. Works on a **seeded demo mailbox with synthetic data**.

**Not included in the MVP:** live bank APIs, SMS ingestion, multi-user accounts,
and a real merchant Index backend.

## Quick start

    git clone https://github.com/<your-username>/hisaab.git
    cd hisaab
    cp .env.example .env        # add your API key
    pip install -r requirements.txt
    python seed_demo_data.py
    python -m hisaab.server     # starts the MCP server
    cd dashboard && npm install && npm run dev

## Demo controls

A judge-facing simulator with four buttons: **Refund Arrives**, **Refund Delayed**,
**Fake Promise Email**, **Duplicate Charge**.

## Evaluation

Extraction and verification accuracy are measured on 30 seeded emails against a
plain-chatbot baseline. Results are in `/benchmarks` (measured, not assumed).

## Disclaimer

Hisaab organizes information and drafts messages. It is **not legal advice**.
Review every draft before sending. Use synthetic data only on free-tier LLM APIs.

## Team

Team [Name]: CMR University, Bengaluru
[Member names]

## License

MIT
