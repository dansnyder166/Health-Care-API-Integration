"""Load Riverside Community lab results from their CSV export into the local data model."""

import csv
import os
from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError

from labs.models import LabResult, Patient, Team

# Canonical test metadata keyed by LOINC code.
# Resolves abbreviations ("Glu") and unit case variations ("MG/DL") to a single
# authoritative form so the data model stays consistent with FHIR-sourced records.
LOINC_CANONICAL = {
    "2339-0":  {"name": "Glucose",                 "unit": "mg/dL"},
    "6299-2":  {"name": "Blood Urea Nitrogen",      "unit": "mg/dL"},
    "2160-0":  {"name": "Creatinine",               "unit": "mg/dL"},
    "718-7":   {"name": "Hemoglobin",               "unit": "g/dL"},
    "6690-2":  {"name": "White Blood Cell Count",   "unit": "10*3/uL"},
    "2823-3":  {"name": "Potassium",                "unit": "mEq/L"},
    "2951-2":  {"name": "Sodium",                   "unit": "mEq/L"},
    "2093-1":  {"name": "Total Cholesterol",        "unit": "mg/dL"},
    "1742-6":  {"name": "ALT",                      "unit": "U/L"},
    "17861-6": {"name": "Calcium",                  "unit": "mg/dL"},
}

# Order matters: try the most specific/common formats first.
_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"]


def _parse_date(raw: str) -> datetime:
    """Return a UTC midnight datetime from a date string in any of the CSV formats."""
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: {raw!r}")


def _make_synthetic_observation(row: dict, effective_dt: datetime) -> dict:
    """Build a FHIR-shaped Observation document from a CSV row.

    Storing synthetic FHIR keeps observation_data consistent with the FHIR
    pipeline so the frontend never needs to know data came from CSV.
    """
    return {
        "resourceType": "Observation",
        "id": row["accession_number"],
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": row["test_code"],
                    "display": row["_canonical_name"],
                }
            ]
        },
        "subject": {"reference": f"Patient/{row['mrn']}"},
        "effectiveDateTime": effective_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "valueQuantity": {
            "value": row["value"],
            "unit": row["_canonical_unit"],
        },
        "identifier": [
            {
                "system": "https://riverside.example.org/accession",
                "value": row["accession_number"],
            }
        ],
    }


class Command(BaseCommand):
    help = "Ingest Riverside Community lab results from CSV into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=None,
            help="Path to CSV file (defaults to DATA_DIR/riverside_community_labs.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing to the database",
        )

    def handle(self, *args, **options):
        csv_path = options["file"]
        if not csv_path:
            data_dir = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "../../../../data"))
            csv_path = os.path.join(data_dir, "riverside_community_labs.csv")

        csv_path = os.path.abspath(csv_path)
        if not os.path.exists(csv_path):
            raise CommandError(f"CSV file not found: {csv_path}")

        try:
            team = Team.objects.get(slug="riverside-community")
        except Team.DoesNotExist:
            raise CommandError(
                "Team 'riverside-community' does not exist. Run seed_data first."
            )

        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database writes"))

        stats = {"rows": 0, "patients_created": 0, "patients_updated": 0,
                 "results_created": 0, "results_updated": 0, "warnings": 0}
        warnings = []

        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for lineno, row in enumerate(reader, start=2):  # 1-based, header is line 1
                stats["rows"] += 1

                # --- date ---
                try:
                    effective_dt = _parse_date(row["collection_date"])
                except ValueError as exc:
                    warnings.append(f"Line {lineno}: {exc} — skipping row")
                    stats["warnings"] += 1
                    continue

                # --- dob ---
                try:
                    dob = _parse_date(row["date_of_birth"]).date()
                except ValueError as exc:
                    warnings.append(f"Line {lineno}: bad date_of_birth {exc} — skipping row")
                    stats["warnings"] += 1
                    continue

                # --- canonical test name & unit ---
                code = row["test_code"].strip()
                canonical = LOINC_CANONICAL.get(code)
                if canonical:
                    canonical_name = canonical["name"]
                    canonical_unit = canonical["unit"]
                else:
                    # Unknown LOINC code: keep whatever the CSV says, just normalise case
                    canonical_name = row["test_name"].strip()
                    canonical_unit = row["unit"].strip()
                    warnings.append(
                        f"Line {lineno}: unknown LOINC code {code!r} — using raw name/unit"
                    )
                    stats["warnings"] += 1

                # --- missing unit ---
                raw_unit = row["unit"].strip()
                if not raw_unit:
                    warnings.append(
                        f"Line {lineno}: missing unit for accession {row['accession_number']} "
                        f"({row['test_name']}) — stored as empty string"
                    )
                    stats["warnings"] += 1

                row["_canonical_name"] = canonical_name
                row["_canonical_unit"] = canonical_unit

                # --- patient name drift ---
                patient_name = row["patient_name"].strip()

                obs_data = _make_synthetic_observation(row, effective_dt)

                if dry_run:
                    continue

                # --- upsert patient (MRN is the identity key, not name) ---
                patient, created = Patient.objects.get_or_create(
                    team=team,
                    mrn=row["mrn"].strip(),
                    defaults={
                        "name": patient_name,
                        "date_of_birth": dob,
                        "patient_data": {
                            "resourceType": "Patient",
                            "id": row["mrn"].strip(),
                            "identifier": [
                                {"type": {"coding": [{"code": "MR"}]}, "value": row["mrn"].strip()}
                            ],
                            "name": [{"text": patient_name}],
                            "birthDate": str(dob),
                        },
                    },
                )
                if created:
                    stats["patients_created"] += 1
                else:
                    stats["patients_updated"] += 1
                    if patient.name != patient_name:
                        warnings.append(
                            f"Line {lineno}: name mismatch for MRN {row['mrn']} "
                            f"(stored: {patient.name!r}, CSV: {patient_name!r}) — keeping stored name"
                        )
                        stats["warnings"] += 1

                # --- upsert lab result ---
                _, result_created = LabResult.objects.update_or_create(
                    accession_number=row["accession_number"].strip(),
                    defaults={
                        "patient": patient,
                        "test_name": canonical_name,
                        "test_code": code,
                        "value": row["value"].strip(),
                        "unit": canonical_unit,
                        "effective_date": effective_dt,
                        "observation_data": obs_data,
                    },
                )
                if result_created:
                    stats["results_created"] += 1
                else:
                    stats["results_updated"] += 1

        # --- report ---
        for w in warnings:
            self.stdout.write(self.style.WARNING(f"  WARNING: {w}"))

        verb = "Would process" if dry_run else "Processed"
        self.stdout.write(self.style.SUCCESS(
            f"\n{verb} {stats['rows']} rows  |  "
            f"patients created={stats['patients_created']} updated={stats['patients_updated']}  |  "
            f"results created={stats['results_created']} updated={stats['results_updated']}  |  "
            f"warnings={stats['warnings']}"
        ))
