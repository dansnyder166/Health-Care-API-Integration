# Riverside Community CSV Normalization Design

## Data Inspection

`data/riverside_community_labs.csv` contains 45 rows across 5 patients (RC-001–RC-005).

### Issues found

| Issue | Example | Decision |
|-------|---------|----------|
| **Multiple date formats** | `03/01/2026`, `2026-03-10`, `3/9/26` | Parse with `dateutil.parser.parse()` which handles all three. Store as a date-only value (no time component in the CSV). We store at midnight UTC in `effective_date`. |
| **Unit case inconsistency** | `mg/dL`, `mg/dl`, `MG/DL` | Normalize to the canonical form via a lookup table keyed on LOINC code. If the code is unknown, lowercase-strip the unit and store as-is. |
| **Test name abbreviations** | `Glu` instead of `Glucose` | Normalize to the canonical display name via the LOINC code lookup table. The LOINC code (e.g. `2339-0`) is authoritative; the display name is derived from it. |
| **Missing unit** | RC-003 Sodium (`RC-2026-044828`) has an empty unit cell | Store an empty string — the value is still clinically meaningful. Do not invent a unit. Log a warning for ops review. |
| **Inconsistent patient name spelling** | `Rodriguez, Maria` vs `Rodriguez, Maria L.` for RC-002 | Treat MRN as the patient identity key, not the name. On `update_or_create(team, mrn)` the last name seen wins. Differences are logged as warnings. |
| **Duplicate accession numbers** | RC-005 has two distinct rows that share the same accession (`RC-2026-044843`, `RC-2026-044844` — actually unique, but within one date) | Each row gets its own accession number; the CSV appears correctly distinct. Upsert by accession number matches the FHIR pipeline behavior. |
| **New patient RC-005** | Not in the seed data (seed has RC-001–RC-004) | Create the patient on first encounter. Same upsert logic as FHIR ingestion. |

### Columns → model fields

| CSV column | Model field | Notes |
|------------|------------|-------|
| `patient_name` | `Patient.name` | Canonical format already "Family, Given" |
| `mrn` | `Patient.mrn` | Identity key together with team |
| `date_of_birth` | `Patient.date_of_birth` | Parse with `dateutil` |
| `test_name` | `LabResult.test_name` | Canonicalized via LOINC lookup |
| `test_code` | `LabResult.test_code` | Stored verbatim |
| `value` | `LabResult.value` | Stored as string (supports `>200`) |
| `unit` | `LabResult.unit` | Case-normalized via LOINC lookup |
| `collection_date` | `LabResult.effective_date` | Parsed date → midnight UTC datetime |
| `accession_number` | `LabResult.accession_number` | Upsert key |

`LabResult.observation_data` is populated with a synthetic JSON document that represents what a FHIR Observation for this record would look like. This keeps the data model consistent with the FHIR pipeline and means the frontend never needs to know the data originated from CSV.

## Pipeline Design

```
CSV file
  → read with csv.DictReader (handles quoted fields)
  → for each row:
      1. parse & validate collection_date (multi-format)
      2. resolve canonical test_name + unit from LOINC code
      3. upsert Patient (team=riverside-community, mrn=row.mrn)
      4. upsert LabResult (accession_number=row.accession_number)
      5. log warnings for any data quality issues
  → print summary: rows processed, patients created/updated, warnings
```

The command is idempotent: re-running it on the same file produces the same database state (upserts, not inserts).

## Decisions & Trade-offs

- **No allergy data in CSV**: The CSV only contains lab results. Allergies are not ingested; this is expected.
- **`observation_data` as synthetic FHIR**: Storing a synthetic FHIR Observation keeps the data model uniform. The alternative (leaving it null) would require frontend changes.
- **Team must pre-exist**: The ingestion command requires `riverside-community` team to exist (created by `seed_data`). It does not create teams — team creation is an admin action.
- **Date stored at midnight UTC**: The CSV has only a date, no time. We store as `00:00:00 UTC` and note this in the synthetic observation's `effectiveDateTime`. This is slightly lossy but explicit — we don't fabricate precision we don't have.
