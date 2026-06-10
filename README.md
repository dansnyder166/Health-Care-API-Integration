# Clinical Lab Data Integration

A Django + React application for viewing lab results from hospital partners.

## Solution Notes

### What was done

| Part | Status | Key files |
|------|--------|-----------|
| A — Bug fixes | ✅ | `backend/labs/serializers.py`, `backend/labs/views.py`, `frontend/src/utils/formatDate.ts` |
| B — Riverside CSV ingestion | ✅ | `backend/labs/management/commands/ingest_riverside_csv.py`, `docs/normalization-design.md` |
| C — Webhook system design | ✅ | `docs/webhook-design.md` |

### Bugs fixed

**#1 — Martinez's penicillin allergy not appearing**
`PatientDetailSerializer.get_allergies()` read criticality from the raw FHIR JSON and silently dropped allergies where that field was `None`. Martinez's penicillin allergy is stored with `criticality=None` (valid: means "unknown"). Fix: replaced the custom method with `PatientAllergySerializer(many=True)`, which reads the model field directly and returns all allergies unconditionally.

**#2 — Riverside patients visible in Lakewood list**
`PatientListView` and `PatientDetailView` used a static `queryset = Patient.objects.all()` with no team scoping. Fix: overrode `get_queryset()` on both views to filter by `team__slug` from the URL kwargs. `LabResultListView` was also tightened to scope by team.

**#3 — "Invalid Date" on some lab results**
`formatDate()` read `observation.effectiveDateTime`, which is absent for ~15% of seed records that use `effectivePeriod` instead (`new Date(undefined)` → `"Invalid Date"`). The backend already normalises the date into `LabResult.effective_date`. Fix: changed `formatDate` to accept an ISO string and updated the call site to pass `result.effective_date`.

### Ingesting Riverside CSV

After seeding the database, run:

```bash
cd backend
python manage.py ingest_riverside_csv
# or point to a specific file:
python manage.py ingest_riverside_csv --file /path/to/riverside_community_labs.csv
# dry-run (validate without writing):
python manage.py ingest_riverside_csv --dry-run
```

The command is idempotent — re-running it on the same file produces the same database state.

### Assumptions

- **Team must exist before CSV ingestion.** The `ingest_riverside_csv` command expects the `riverside-community` team to already be present (created by `seed_data`). It does not create teams — team creation is an admin action.
- **Date stored at midnight UTC for CSV records.** The CSV supplies only a date, no time. Results are stored as `00:00:00 UTC`. This is noted in the synthetic FHIR `observation_data` that each result carries, so the representation is explicit rather than misleading.
- **CSV unit/name normalization is LOINC-authoritative.** Abbreviations (`Glu`) and unit case variations (`MG/DL`, `mg/dl`) are resolved to canonical values via the LOINC code. If a LOINC code is unrecognised, the raw CSV values are stored and a warning is logged.
- **The webhook design assumes HMAC-SHA256 shared-secret authentication.** No OAuth2 / mTLS is specified. This is sufficient for a single hospital integration and matches the pattern used for the rest of the integrations.
- **Migrations were generated locally.** `backend/labs/migrations/0001_initial.py` is included in the repo. If you are running against a fresh database without Docker, run `python manage.py migrate` before `seed_data`.

---

## Quick Start (Docker)

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173

The database is automatically migrated and seeded on first run.

## Local Setup (no Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Running Tests

```bash
cd backend
pytest
```

## Project Structure

```
backend/         Django 5 + DRF API
  config/        Django settings, root URL conf
  labs/          Models, serializers, views, FHIR utilities
frontend/        React 18 + TypeScript + Vite + Tailwind
  src/
    api/         API client
    components/  React components
    utils/       Utility functions
data/            Hospital data files
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/teams/<slug>/patients/` | List patients for a team |
| `GET /api/teams/<slug>/patients/<id>/` | Patient detail with allergies and lab results |
| `GET /api/teams/<slug>/patients/<id>/lab-results/` | Paginated lab results for a patient |

## Assignment

See `assignment.md` for the full assignment description.
