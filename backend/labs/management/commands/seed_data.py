import random
from datetime import date, datetime, timedelta, timezone

from django.core.management.base import BaseCommand

from labs.models import LabResult, Patient, PatientAllergy, Team

LAB_TESTS = [
    {"name": "Glucose", "code": "2339-0", "unit": "mg/dL", "low": 70, "high": 110},
    {"name": "Blood Urea Nitrogen", "code": "6299-2", "unit": "mg/dL", "low": 7, "high": 20},
    {"name": "Creatinine", "code": "2160-0", "unit": "mg/dL", "low": 0.6, "high": 1.2},
    {"name": "Hemoglobin", "code": "718-7", "unit": "g/dL", "low": 12.0, "high": 17.0},
    {"name": "White Blood Cell Count", "code": "6690-2", "unit": "10*3/uL", "low": 4.5, "high": 11.0},
    {"name": "Potassium", "code": "2823-3", "unit": "mEq/L", "low": 3.5, "high": 5.0},
    {"name": "Sodium", "code": "2951-2", "unit": "mEq/L", "low": 136, "high": 145},
    {"name": "Total Cholesterol", "code": "2093-1", "unit": "mg/dL", "low": 125, "high": 200},
    {"name": "ALT", "code": "1742-6", "unit": "U/L", "low": 7, "high": 56},
    {"name": "Calcium", "code": "17861-6", "unit": "mg/dL", "low": 8.5, "high": 10.5},
]

LAKEWOOD_PATIENTS = [
    {"mrn": "LM-001", "name": "Chen, David", "dob": "1978-04-12"},
    {"mrn": "LM-002", "name": "Okafor, Grace", "dob": "1985-09-23"},
    {"mrn": "LM-003", "name": "Martinez, Sofia", "dob": "1992-01-07"},
    {"mrn": "LM-004", "name": "Williams, Robert", "dob": "1965-11-30"},
]

RIVERSIDE_PATIENTS = [
    {"mrn": "RC-001", "name": "Garcia, Ana", "dob": "1988-06-15"},
    {"mrn": "RC-002", "name": "Thompson, James", "dob": "1973-03-21"},
    {"mrn": "RC-003", "name": "Kim, Sarah", "dob": "1995-08-09"},
    {"mrn": "RC-004", "name": "Okafor, Emmanuel", "dob": "1960-12-02"},
]


class Command(BaseCommand):
    help = "Seed the database with sample hospital data"

    def handle(self, *args, **options):
        if Team.objects.exists():
            self.stdout.write(self.style.WARNING("Database already seeded, skipping."))
            return

        random.seed(42)
        self.stdout.write("Seeding database...")

        lakewood = Team.objects.create(name="Lakewood Memorial", slug="lakewood-memorial")
        riverside = Team.objects.create(name="Riverside Community", slug="riverside-community")

        lw_patients = self._create_patients(lakewood, LAKEWOOD_PATIENTS)
        rv_patients = self._create_patients(riverside, RIVERSIDE_PATIENTS)

        for patient in lw_patients + rv_patients:
            self._create_lab_results(patient)

        self._create_allergies(lw_patients)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {Patient.objects.count()} patients, "
            f"{LabResult.objects.count()} lab results, "
            f"{PatientAllergy.objects.count()} allergies"
        ))

    def _create_patients(self, team, patient_list):
        patients = []
        for p in patient_list:
            patient = Patient.objects.create(
                team=team,
                mrn=p["mrn"],
                name=p["name"],
                date_of_birth=date.fromisoformat(p["dob"]),
                patient_data=self._make_fhir_patient(p, team),
            )
            patients.append(patient)
        return patients

    def _make_fhir_patient(self, patient_info, team):
        name_parts = patient_info["name"].split(", ")
        return {
            "resourceType": "Patient",
            "id": patient_info["mrn"],
            "identifier": [
                {
                    "type": {"coding": [{"code": "MR"}]},
                    "value": patient_info["mrn"],
                }
            ],
            "name": [{"family": name_parts[0], "given": [name_parts[1]]}],
            "birthDate": patient_info["dob"],
            "managingOrganization": {"display": team.name},
        }

    def _create_lab_results(self, patient):
        base_date = datetime(2026, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        accession_seq = 1000

        for i in range(30):
            test = random.choice(LAB_TESTS)
            days_offset = random.randint(0, 60)
            hours_offset = random.randint(0, 12)
            dt = base_date + timedelta(days=days_offset, hours=hours_offset)
            value = round(random.uniform(test["low"] * 0.8, test["high"] * 1.3), 1)
            accession = f"{patient.mrn}-{accession_seq + i}"

            # Vary the FHIR date representation to create realistic data:
            # ~70% standard effectiveDateTime with timezone
            # ~15% effectivePeriod (used for timed collections)
            # ~15% effectiveDateTime without timezone suffix
            roll = random.random()
            if roll < 0.15:
                variant = "period"
            elif roll < 0.30:
                variant = "no_tz"
            else:
                variant = "standard"

            obs_data = self._make_fhir_observation(
                test, value, dt, accession, patient.mrn, variant
            )

            LabResult.objects.create(
                patient=patient,
                accession_number=accession,
                test_name=test["name"],
                test_code=test["code"],
                value=str(value),
                unit=test["unit"],
                effective_date=dt,
                observation_data=obs_data,
            )

    def _make_fhir_observation(self, test, value, dt, accession, patient_mrn, variant):
        obs = {
            "resourceType": "Observation",
            "id": accession,
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": test["code"],
                        "display": test["name"],
                    }
                ]
            },
            "subject": {"reference": f"Patient/{patient_mrn}"},
            "valueQuantity": {
                "value": value,
                "unit": test["unit"],
                "system": "http://unitsofmeasure.org",
                "code": test["unit"],
            },
            "identifier": [
                {
                    "system": "https://lakewood.example.org/accession",
                    "value": accession,
                }
            ],
        }

        if variant == "period":
            obs["effectivePeriod"] = {
                "start": dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
                "end": (dt + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            }
        elif variant == "no_tz":
            obs["effectiveDateTime"] = dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            obs["effectiveDateTime"] = dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

        return obs

    def _create_allergies(self, patients):
        allergy_data_sets = {
            "LM-001": [
                ("Sulfa drugs", "high"),
                ("Aspirin", "low"),
            ],
            "LM-002": [
                ("Latex", "unable-to-assess"),
            ],
            "LM-003": [
                ("Penicillin", None),
                ("Ibuprofen", "low"),
            ],
            "LM-004": [
                ("Codeine", "high"),
                ("Peanuts", "high"),
                ("Shellfish", "low"),
            ],
        }

        for patient in patients:
            entries = allergy_data_sets.get(patient.mrn, [])
            for substance, criticality in entries:
                fhir_data = {
                    "resourceType": "AllergyIntolerance",
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                "code": "active",
                            }
                        ]
                    },
                    "verificationStatus": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                                "code": "confirmed",
                            }
                        ]
                    },
                    "code": {
                        "coding": [{"display": substance}],
                    },
                    "patient": {"reference": f"Patient/{patient.mrn}"},
                    "criticality": criticality,
                }
                PatientAllergy.objects.create(
                    patient=patient,
                    substance=substance,
                    criticality=criticality,
                    allergy_data=fhir_data,
                )
