# Riverside Webhook Ingestion — System Design

## Problem Statement

Riverside Community Hospital will switch from daily CSV batch exports to real-time FHIR R4 Bundle delivery via HTTP webhook. Key requirements:

- ~5,000 results/day in payloads of 1–50 Observations
- Results must appear in dashboard within **5 minutes** of receipt
- Endpoint must respond within **3 seconds** (hospital HTTP timeout)
- The hospital **retries on timeout** — same payload can arrive multiple times
- Results may be **corrections** of a previously sent result (same accession number, updated value)
- Observable: ops must know when things go wrong
- Stack: Django, Celery, Redis, PostgreSQL

---

## High-Level Flow

```
Hospital
  → POST /api/webhooks/riverside/fhir-bundle/
      ↓
  [Django view] — validates signature, enqueues task, returns 202 in <200ms
      ↓
  [Redis queue]
      ↓
  [Celery worker] — parses bundle, upserts records, logs result
      ↓
  [PostgreSQL] — patients + lab results updated
      ↓
  [Frontend] — reads updated data within 5 minutes
```

---

## Component Design

### 1. Webhook Endpoint

**URL:** `POST /api/webhooks/riverside/fhir-bundle/`

The endpoint does the minimum work needed to respond within 3 seconds:

1. **Authenticate** — verify HMAC-SHA256 signature on the request body using a shared secret stored in Django settings (not hardcoded). Reject with `401` if invalid. This prevents replay attacks and accidental data from third parties.
2. **Deserialise** — parse JSON body; reject with `400` if malformed.
3. **Idempotency key** — compute `SHA256(raw_body)` as a fingerprint. Check a small Redis set (TTL 48h) of recently-seen fingerprints. If already seen, return `200 {"status": "duplicate"}` immediately without enqueuing — this handles the hospital's retry-on-timeout behavior without double-processing.
4. **Enqueue** — push a Celery task with the raw bundle JSON payload. The task ID is stored alongside the fingerprint.
5. **Respond** — return `202 Accepted {"task_id": "<uuid>"}` within target of < 500ms.

The endpoint never touches PostgreSQL in the hot path. All I/O is Redis-only.

**Why 202 not 200?** The hospital only requires a response within 3s — it does not require the results to be persisted before we respond. Returning 202 honestly communicates "received, processing asynchronously."

---

### 2. Celery Task

**Task name:** `labs.tasks.process_fhir_bundle`

```python
@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,   # only ack after successful processing
)
def process_fhir_bundle(self, team_slug: str, bundle: dict, delivery_id: str):
    ...
```

The task reuses the existing `labs.fhir.process_fhir_bundle()` function, which already:
- Upserts patients by MRN
- Upserts lab results by accession number (so corrections overwrite the original)
- Returns a stats dict with error details

Additional responsibilities at the task level:

- **Structured logging** on start, success, and failure with `team_slug`, `delivery_id`, bundle size, and outcome stats.
- **Retry on transient failures** (DB deadlock, network error to downstream). On permanent failure (bad FHIR structure), log and do not retry — raise a non-retryable exception so Celery marks the task failed.
- **Dead-letter tracking** — failed tasks after max_retries are routed to a `failed_bundles` queue. A separate alerting consumer reads this queue and fires a PagerDuty/Slack alert.

**Correction handling** — the existing `LabResult.objects.update_or_create(accession_number=...)` already handles corrections correctly: if a bundle contains an Observation with status `corrected` for an accession number that already exists, the row is overwritten with the new value. No special logic needed.

---

### 3. Idempotency Store (Redis)

```
Key:   webhook:seen:{SHA256(raw_body)}
Value: task_id
TTL:   48 hours
```

48 hours covers any realistic retry window while keeping Redis memory bounded. With 5,000 deliveries/day and ~100 bytes per key, this is ~500KB — negligible.

---

### 4. Multi-hospital Extensibility

The URL pattern encodes the hospital slug: `/api/webhooks/{hospital_slug}/fhir-bundle/`. A `WebhookSource` model (or Django settings dict) maps slug → Team + shared secret. Adding a new hospital is a data/config change, not a code change.

```python
# config/settings.py
WEBHOOK_SOURCES = {
    "riverside": {
        "team_slug": "riverside-community",
        "secret": env("RIVERSIDE_WEBHOOK_SECRET"),
    },
}
```

---

### 5. Observability

| Signal | Mechanism |
|--------|-----------|
| Endpoint latency | Django middleware timing + Datadog/Prometheus histogram |
| Task queue depth | Celery Flower or `redis LLEN` on the queue key; alert if > 500 |
| Task success/failure rate | Celery task result backend + structured log aggregation |
| Duplicate delivery rate | Counter incremented on Redis cache hit; useful for capacity planning |
| Dead-letter queue | Alert on any message in `failed_bundles` queue |
| End-to-end latency | Log `received_at` on enqueue and `persisted_at` on task completion; alert if p95 > 4 min |

All task logs include `delivery_id`, `team_slug`, bundle size, and outcome. This gives ops a complete audit trail — they can replay a specific delivery by re-enqueuing its `delivery_id`.

---

### 6. Capacity & SLO Analysis

- 5,000 results/day ≈ 0.06 results/second average. Even if clustered at peak: 5× burst = 0.3 RPS on the endpoint.
- At 50 results per payload, that's at most 100 payloads/day. One Celery worker is sufficient; two provides redundancy.
- A single Celery task processes a 50-result bundle in < 1 second (50 SQL upserts). P99 processing time well under the 5-minute SLO even with queue buildup.
- The 5-minute SLO has ~300× headroom at steady state. The constraint that would erode it is a queue backup during a DB incident — this is why task queue depth alerting matters.

---

## What Is Not In This Design

- **Schema versioning**: FHIR R4 is assumed stable. If Riverside upgrades to R5, a version negotiation layer would be needed.
- **Authentication beyond HMAC**: mTLS or OAuth2 could replace or supplement HMAC. HMAC is sufficient for this integration given the shared-secret model the hospital already uses.
- **Result pagination in the API**: The 5-minute latency SLO applies to ingestion, not API response time. API pagination is a separate concern.

---

## Design Gaps / Future Improvements

- **Idempotency robustness**
  Current deduplication uses `SHA256(raw_body)`, which only detects byte-identical retries. Semantically identical bundles with different serialization may bypass this check. A more robust approach would use `Bundle.identifier`, a delivery ID, or enforce idempotency at the resource level (e.g. per `accession_number` / `Observation.id`).

- **Replay attack protection**
  HMAC authentication ensures integrity but does not prevent replay attacks. Production systems should include timestamp validation (and optionally nonces) to enforce request freshness — a common convention is to reject requests whose timestamp header falls outside a ±5-minute window.

- **Correction vs. duplicate distinction**
  The system overwrites records via `update_or_create(accession_number=...)`, but does not distinguish between duplicate deliveries and true clinical corrections. Version tracking or audit history (e.g. append-only event log alongside the current-state record) could improve traceability and support clinical audit requirements.

- **Dead-letter replay strategy**
  While failed bundles are captured in a dead-letter queue, the replay mechanism is implicit. A defined operational process — for example, re-enqueuing a specific bundle by `delivery_id` via a management command or admin action — would improve clarity and reduce the risk of accidental double-processing during incident recovery.
