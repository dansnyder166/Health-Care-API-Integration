# Clinical Lab Data Integration

## Overview

You're joining the integrations team. We build and maintain connections between hospital systems and our platform.

A hospital partner integration (Lakewood Memorial) is partially built and in production, but users have reported issues. A second hospital (Riverside Community) needs to be onboarded.

| Part | What You'll Do                          | Weight | Suggested Time |
| ---- | --------------------------------------- | ------ | -------------- |
| A    | Investigate and fix reported bugs       | 25%    | ~1 hour        |
| B    | Ingest data from a new hospital partner | 35%    | ~1.5 hours     |
| C    | Design the next iteration of the system | 40%    | ~1 hour        |

**Total: 3–4 hours**

---

## What You Receive

A starter repo with a Django + React application for viewing lab results from hospital partners. The backend ingests FHIR R4 data, stores it locally, and serves it through a REST API. The frontend displays patient information, lab results, and allergy data.

The app runs with Docker Compose (`docker compose up --build`) or locally (see the README). Seed data is loaded automatically. All existing tests pass.

Explore the codebase to understand the data model and how data flows through the system before starting.

---

## Part A: Bug Investigation

Clinical users at Lakewood Memorial have filed these bug reports:

**#1**

> "Patient Martinez's allergy list shows 'No known allergies' but she definitely has a penicillin allergy — I documented it myself. Can you check why it's not showing up?"
>
> — Sarah, RN

**#2**

> "I'm seeing patients from Riverside Community mixed into our Lakewood Memorial patient list. That shouldn't happen — we should only see our own patients."
>
> — Dr. Chen

**#3**

> "Some lab result dates show as 'Invalid Date' on the dashboard. It seems random — not all of them, just some. Makes it hard to review trends."
>
> — James, Lab Technician

Fix each bug and document what you found. Show us how you'd communicate this to the team — what broke, why, and how you tracked it down.

---

## Part B: New Hospital Onboarding

Riverside Community Hospital exports their lab data as CSV. You'll find their export in `data/riverside_community_labs.csv`.

Before writing code, inspect the data and write a brief plan for how you'll approach the ingestion. Save it as `docs/normalization-design.md`.

Then build a pipeline that loads the CSV into the existing data model. Not every row will be straightforward — document the decisions you make along the way.

---

## Part C: System Design

Riverside wants to move from CSV batch exports to real-time data delivery. They'll send FHIR R4 Bundles via webhook as lab results are finalized — approximately 5,000 results per day, in payloads of 1–50 results each.

A sample payload is in `data/sample_webhook_payload.json`. Note that it includes a correction of a previously sent result — this is a regular occurrence, distinct from a duplicate delivery.

**Constraints:**

- Results must appear in the dashboard within 5 minutes of receipt
- The hospital may retry on timeout — same payload delivered multiple times
- The webhook endpoint must respond within 3 seconds (hospital's HTTP timeout)
- The system must be observable — ops needs to know when things go wrong
- Stack: Django, Celery, Redis, PostgreSQL
- Other hospitals will be onboarded in the future

**No code required.** Write a design document (1–2 pages) that would let another engineer on the team implement this.

We care about your reasoning, not just your conclusions.

---

## Submission

1. Push your solution to a private GitHub repo and share access
2. Make sure the repo includes your code changes and both design docs
3. Include a brief README noting any setup steps or assumptions

We'll follow up with a live session to discuss your approach.