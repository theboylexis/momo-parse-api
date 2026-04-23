# Data Minimization Audit

MomoParse's privacy story rests on a specific, auditable claim: **raw SMS text is never persisted to durable storage.** This document traces every pathway raw SMS takes through the system, names the durable stores, and honestly records both what is *not* retained and what *is*. Written for the paper's ethical considerations section and as evidence a licensed lender or regulator can evaluate directly against the code.

Last audited: 2026-04-22. Re-run this audit whenever a persistence layer is added or the parse path changes.

---

## Scope of the claim

"Persistence" here means any write to storage that outlives the HTTP request. Specifically:

- Database rows (PostgreSQL in production via `DATABASE_URL`, SQLite locally)
- Disk files (log files, JSON profile snapshots)
- Structured log output ingested by Railway logs, Datadog, or similar
- Webhook payloads posted to caller-supplied URLs

Transient in-memory retention during the lifetime of a single request (or a single async job) is out of scope — Python's garbage collector reclaims the SMS string once the function frame exits, and no request-lived object is ever serialised to storage.

---

## Entry points — where raw SMS enters the system

| Endpoint | File | Handler |
|---|---|---|
| `POST /v1/parse` | [api/routes/parse.py:84](../api/routes/parse.py#L84) | `parse_single` |
| `POST /v1/parse/batch` | [api/routes/parse.py:113](../api/routes/parse.py#L113) | `parse_batch` |
| `POST /v1/enrich` | [api/routes/enrich.py:96](../api/routes/enrich.py#L96) | `enrich` |
| `POST /v1/profile` | [api/routes/enrich.py:155](../api/routes/enrich.py#L155) | `profile` |
| `POST /v1/report` | [api/routes/report.py:53](../api/routes/report.py#L53) | `report` |

Raw SMS arrives in each handler via the Pydantic-validated request body as `body.sms_text` (single) or `msg.sms_text` (batch items).

---

## Per-pathway verdict

### Sync parse paths (`/v1/parse`, `/v1/parse/batch`, and sync-mode `/v1/enrich`, `/v1/profile`, `/v1/report`)

- `p.parse(sms_text, sender_id=...)` is invoked. It returns a structured `ParseResult` carrying only extracted fields — no raw SMS.
- The SMS string is never attached to the response model, never logged, never written to disk.
- At function return, the request body goes out of scope and is garbage-collected.

**Verdict: no persistence.**

### Async job paths (`/v1/enrich`, `/v1/profile`, `/v1/report` with ≥500 SMS)

- The handler constructs `messages_raw = [{"sms_text": m.sms_text, "sender_id": m.sender_id}]` ([api/routes/enrich.py:114-117](../api/routes/enrich.py#L114-L117)) and schedules `run_enrich_job` as a FastAPI `BackgroundTask`.
- `messages_raw` lives only in the background task's stack frame. It is **not** written to the database when the `Job` record is created — see [enricher/jobs.py:53-73](../enricher/jobs.py#L53-L73): only `job_id`, `status`, `webhook_url`, and `message_count` are persisted.
- Inside `run_enrich_job` ([enricher/jobs.py:143-215](../enricher/jobs.py#L143-L215)), each SMS is parsed + categorized into structured `tx_dicts`. The raw SMS string is used once per iteration and discarded.
- The completed job result stored via `_set_complete(job, result_payload)` contains only the analytics payload (income totals, category breakdowns, indexes, driver decompositions, etc.) — no `sms_text`.

**Verdict: no persistence. Transient in-memory retention during job execution only.**

### Webhook delivery

- When a caller provides `webhook_url`, `_deliver_webhook` posts `result_payload` to it ([enricher/jobs.py:135-140](../enricher/jobs.py#L135-L140)). The payload is the same analytics object stored in `JobRecord.result` — no raw SMS.

**Verdict: no raw SMS leaves the system via webhook.**

### Drift telemetry

- Every fuzzy fallback emits a `parse.fuzzy_fallback` log event via [parser/telemetry.py](../parser/telemetry.py). The event body is explicit: `telco`, `template_id`, `similarity`, `confidence`, `captured_fields`, `missing_critical_fields`, `sms_length`, and a **16-character SHA-256 prefix** of the SMS for correlation.
- The raw SMS is never included in the log record. The source file's docstring states this as an invariant: `No raw SMS content is logged — only a 16-char SHA-256 prefix for correlation — so PII never reaches log storage.`

**Verdict: no persistence of raw SMS in telemetry.**

### Database schema

[db/models.py](../db/models.py) defines exactly two tables:

- `JobRecord` — fields: `job_id`, `status`, `created_at`, `completed_at`, `result` (JSON analytics), `error`, `webhook_url`, `message_count`. **No `sms_text` column.**
- `CounterpartyProfile` — fields: `key`, `counts`, `updated_at`. **No `sms_text` column.** See "What *is* retained" below.

**Verdict: schema has no capacity for raw SMS. This is enforced at the type level.**

### Access logs

Uvicorn default access logs record request method, path, status, and latency — **not request bodies**. The API log configuration in [api/logging_config.py](../api/logging_config.py) emits structured JSON events but the handlers never place `sms_text` into `logger.extra=`.

**Verdict: no raw SMS in access or application logs.**

---

## What *is* retained (honest disclosure)

Two categories of derived data persist beyond the request lifetime. Neither is raw SMS, but both are user-traceable and must be disclosed.

### 1. Counterparty intelligence store

- **Source:** [categorizer/counterparty.py](../categorizer/counterparty.py), table `CounterpartyProfile`.
- **What's stored:** for each counterparty seen in any user's transactions, a `key` (the counterparty's phone number if available, otherwise their uppercased name) and a histogram of how many times each financial category has been assigned to transactions involving them.
- **Why:** this is the categorizer's Layer 3 — once a counterparty has been seen ≥3 times with ≥70% of transactions in one category, it becomes a strong prior that corrects low-confidence ML predictions. The docstring frames it as a "data moat."
- **User isolation:** **none.** The store is global across API consumers. If user A transacts with a merchant and user B transacts with the same merchant, both contribute to the same `CounterpartyProfile` row.
- **Retention:** indefinite. There is no current TTL or deletion mechanism.

**Paper-honest framing:** "MomoParse retains counterparty identifiers (phone numbers or names, never full SMS text) in a global categorizer-improvement store, with per-category transaction-count histograms. This is a derivation of user data, not raw input, but it is identifying and persistent — disclosed to API consumers and subject to revision under a future data-subject-rights interface."

### 2. Analytics payloads in `JobRecord.result`

- **Source:** [enricher/jobs.py](../enricher/jobs.py) stores the full analytics payload as JSON in `JobRecord.result` so async callers can poll for results.
- **What's stored:** aggregates (income totals, category breakdowns, financial indexes), and for profile-mode jobs, the `top_counterparties` list which contains identifier + amount + count per counterparty.
- **Why:** async job semantics require the result to outlive the triggering request so polling works.
- **Retention:** indefinite (no TTL currently implemented).

**Paper-honest framing:** "Completed async job results persist in the jobs table so callers can poll. Results contain derived aggregates (not raw SMS), and for profile endpoints include identifier-level counterparty lists. A TTL on job results is a known compliance gap."

---

## Known gaps (flagged for follow-up, not silently elided)

1. **No TTL on `JobRecord.result` or `CounterpartyProfile`.** Both persist indefinitely. Data-subject deletion requests cannot be honoured with the current schema. Remedy: add `expires_at` with a configurable default (e.g. 90 days) and a background reaper.
2. **No user isolation on the counterparty store.** A legitimate design choice for the "data moat," but should be surfaced in the API terms and the paper's ethics section, not assumed invisible.
3. **`counterparty_profiles.json` on disk in local/non-DB mode.** Exists for dev convenience; should not run in production. Should be gated behind an explicit dev flag.
4. **No data-subject-rights (DSR) endpoint.** DPA 2012 and BoG guidance expect a mechanism for users to inspect and delete data derived from their activity. Not implemented.
5. **Exception messages in logs.** `logger.error("Job %s failed: %s", ..., str(exc))` ([enricher/jobs.py:132](../enricher/jobs.py#L132)) could theoretically leak SMS fragments if a parser exception contained them. Currently no known parser exception includes SMS text, but a regression guard test would harden this.

---

## Recommended next engineering changes

- **Test:** a pytest that runs a representative request through every endpoint and asserts `sms_text` substrings never appear in (a) the response JSON, (b) captured log records, (c) the job result payload. Pins the invariant in CI.
- **TTL:** add `expires_at` to both `JobRecord` and `CounterpartyProfile`, default 90 days, with a scheduled cleanup task.
- **DSR endpoint:** `DELETE /v1/counterparty/{key}` and `DELETE /v1/jobs/{job_id}` exposed to authenticated callers with appropriate scopes.
- **Docs:** README "Privacy" section linking to this audit.

---

## Paper framing (section to add — Ethical Considerations)

> **Data minimization.** MomoParse does not persist raw SMS text. We audited every entry point (five public endpoints) and every storage mechanism (two database tables, disk files, structured logs, webhook delivery) and confirmed that raw SMS is used transiently during request handling and is discarded once structured fields are extracted. The one exception is a sixteen-character SHA-256 prefix emitted with drift-telemetry events for correlation — insufficient to reconstruct content. This reflects a design choice consistent with Ghana's Data Protection Act 2012 principle of minimization and with the "user-owned" framing: the user's SMS remains on the user's device; MomoParse receives it, extracts structured fields, and forgets the original text.
>
> Two derivations of user data do persist beyond request lifetime: a counterparty intelligence store that aggregates per-counterparty category histograms across API consumers to improve categorization accuracy, and completed async job results held for polling. Both are derived (not raw) data, but we disclose them explicitly: neither has a current TTL, the counterparty store is not user-isolated, and no data-subject-rights endpoint is currently exposed. These are known gaps, flagged here rather than elided. Future work includes adding configurable retention windows, user-scoped counterparty stores, and DSR endpoints before any production deployment with real user data.

---

**Audit hash:** this document reflects the repository state at commit — regenerate whenever persistence or logging behaviour changes.
