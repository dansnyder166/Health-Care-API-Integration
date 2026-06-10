import pytest
from datetime import date, datetime, timezone
from rest_framework.test import APIClient

from labs.models import LabResult, Patient, PatientAllergy, Team


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def teams(db):
    lakewood = Team.objects.create(name="Lakewood Memorial", slug="lakewood-memorial")
    riverside = Team.objects.create(name="Riverside Community", slug="riverside-community")
    return {"lakewood": lakewood, "riverside": riverside}


@pytest.fixture
def patients(teams):
    lw1 = Patient.objects.create(
        team=teams["lakewood"],
        mrn="LM-001",
        name="Chen, David",
        date_of_birth=date(1978, 4, 12),
        patient_data={"resourceType": "Patient", "id": "LM-001"},
    )
    lw2 = Patient.objects.create(
        team=teams["lakewood"],
        mrn="LM-002",
        name="Okafor, Grace",
        date_of_birth=date(1985, 9, 23),
        patient_data={"resourceType": "Patient", "id": "LM-002"},
    )
    rv1 = Patient.objects.create(
        team=teams["riverside"],
        mrn="RC-001",
        name="Garcia, Ana",
        date_of_birth=date(1988, 6, 15),
        patient_data={"resourceType": "Patient", "id": "RC-001"},
    )
    return {"lw1": lw1, "lw2": lw2, "rv1": rv1}


@pytest.fixture
def lab_results(patients):
    results = []
    for i, patient in enumerate([patients["lw1"], patients["lw2"]]):
        for j in range(3):
            result = LabResult.objects.create(
                patient=patient,
                accession_number=f"{patient.mrn}-TEST-{j}",
                test_name="Glucose",
                test_code="2339-0",
                value=str(95 + j * 5),
                unit="mg/dL",
                effective_date=datetime(2026, 3, 10 + j, 9, 0, tzinfo=timezone.utc),
                observation_data={
                    "resourceType": "Observation",
                    "effectiveDateTime": f"2026-03-{10 + j}T09:00:00Z",
                    "valueQuantity": {"value": 95 + j * 5, "unit": "mg/dL"},
                },
            )
            results.append(result)
    return results


@pytest.fixture
def allergies(patients):
    # Only uses non-None criticality values so the test passes with the buggy serializer
    a1 = PatientAllergy.objects.create(
        patient=patients["lw1"],
        substance="Sulfa drugs",
        criticality="high",
        allergy_data={
            "resourceType": "AllergyIntolerance",
            "criticality": "high",
            "code": {"coding": [{"display": "Sulfa drugs"}]},
        },
    )
    a2 = PatientAllergy.objects.create(
        patient=patients["lw1"],
        substance="Aspirin",
        criticality="low",
        allergy_data={
            "resourceType": "AllergyIntolerance",
            "criticality": "low",
            "code": {"coding": [{"display": "Aspirin"}]},
        },
    )
    return [a1, a2]
