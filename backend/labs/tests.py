import pytest
from datetime import datetime, timezone
from labs.models import LabResult, Patient, PatientAllergy


@pytest.mark.django_db
class TestPatientListAPI:
    def test_returns_patients(self, api_client, patients):
        response = api_client.get("/api/teams/lakewood-memorial/patients/")
        assert response.status_code == 200
        assert len(response.data["results"]) > 0

    def test_includes_patient_fields(self, api_client, patients):
        response = api_client.get("/api/teams/lakewood-memorial/patients/")
        patient = response.data["results"][0]
        assert "name" in patient
        assert "mrn" in patient
        assert "date_of_birth" in patient
        assert "team_name" in patient


@pytest.mark.django_db
class TestPatientDetailAPI:
    def test_returns_patient(self, api_client, patients):
        patient = patients["lw1"]
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patient.id}/"
        )
        assert response.status_code == 200
        assert response.data["name"] == "Chen, David"
        assert response.data["mrn"] == "LM-001"

    def test_includes_allergies(self, api_client, patients, allergies):
        patient = patients["lw1"]
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patient.id}/"
        )
        assert response.status_code == 200
        assert len(response.data["allergies"]) == 2

    def test_includes_lab_results(self, api_client, patients, lab_results):
        patient = patients["lw1"]
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patient.id}/"
        )
        assert response.status_code == 200
        assert len(response.data["lab_results"]) == 3


@pytest.mark.django_db
class TestLabResultAPI:
    def test_returns_lab_results(self, api_client, patients, lab_results):
        patient = patients["lw1"]
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patient.id}/lab-results/"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 3

    def test_lab_result_fields(self, api_client, patients, lab_results):
        patient = patients["lw1"]
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patient.id}/lab-results/"
        )
        result = response.data["results"][0]
        assert "test_name" in result
        assert "value" in result
        assert "unit" in result
        assert "effective_date" in result
        assert "observation_data" in result


@pytest.mark.django_db
class TestBugFixes:
    """Regression tests for the three reported bugs."""

    def test_bug1_allergy_with_null_criticality_is_returned(self, api_client, patients):
        """Bug #1: Allergies with no criticality were silently dropped from the response."""
        PatientAllergy.objects.create(
            patient=patients["lw1"],
            substance="Penicillin",
            criticality=None,
            allergy_data={
                "resourceType": "AllergyIntolerance",
                "code": {"coding": [{"display": "Penicillin"}]},
                # No "criticality" key — mirrors the real Martinez seed data
            },
        )
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patients['lw1'].id}/"
        )
        assert response.status_code == 200
        substances = [a["substance"] for a in response.data["allergies"]]
        assert "Penicillin" in substances

    def test_bug2_patient_list_is_scoped_to_team(self, api_client, patients):
        """Bug #2: Patient list returned patients from all teams, not just the requested one."""
        response = api_client.get("/api/teams/lakewood-memorial/patients/")
        assert response.status_code == 200
        team_names = {p["team_name"] for p in response.data["results"]}
        assert team_names == {"Lakewood Memorial"}

    def test_bug2_patient_detail_is_scoped_to_team(self, api_client, patients):
        """Bug #2: A patient from Riverside must not be accessible via the Lakewood slug."""
        riverside_patient = patients["rv1"]
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{riverside_patient.id}/"
        )
        assert response.status_code == 404

    def test_bug3_effective_date_is_present_in_lab_result(self, api_client, patients, lab_results):
        """Bug #3: effective_date on LabResult must be a parseable ISO string for the frontend."""
        response = api_client.get(
            f"/api/teams/lakewood-memorial/patients/{patients['lw1'].id}/lab-results/"
        )
        assert response.status_code == 200
        for result in response.data["results"]:
            assert result["effective_date"] is not None
            # Must parse without raising
            datetime.fromisoformat(str(result["effective_date"]).replace("Z", "+00:00"))

    def test_bug3_effective_date_populated_from_effective_period(self, teams):
        """Bug #3: FHIR Observations using effectivePeriod must store a valid effective_date."""
        from labs.fhir import process_fhir_bundle

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "identifier": [{"type": {"coding": [{"code": "MR"}]}, "value": "BUG3-PT"}],
                        "name": [{"family": "Test", "given": ["Period"]}],
                        "birthDate": "1990-01-01",
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "status": "final",
                        "code": {"coding": [{"code": "2339-0", "display": "Glucose"}]},
                        "subject": {"reference": "Patient/BUG3-PT"},
                        # effectivePeriod instead of effectiveDateTime
                        "effectivePeriod": {
                            "start": "2026-03-10T09:00:00Z",
                            "end": "2026-03-10T09:15:00Z",
                        },
                        "valueQuantity": {"value": 95, "unit": "mg/dL"},
                        "identifier": [{"value": "BUG3-ACC-001"}],
                    }
                },
            ],
        }

        process_fhir_bundle(bundle, teams["lakewood"])
        result = LabResult.objects.get(accession_number="BUG3-ACC-001")
        assert result.effective_date is not None


@pytest.mark.django_db
class TestFHIRIngestion:
    def test_process_fhir_bundle(self, teams):
        from labs.fhir import process_fhir_bundle

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "test-pt",
                        "identifier": [
                            {"type": {"coding": [{"code": "MR"}]}, "value": "TEST-001"}
                        ],
                        "name": [{"family": "Test", "given": ["Patient"]}],
                        "birthDate": "1990-01-01",
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "test-obs",
                        "status": "final",
                        "code": {
                            "coding": [
                                {"system": "http://loinc.org", "code": "2339-0", "display": "Glucose"}
                            ]
                        },
                        "subject": {"reference": "Patient/TEST-001"},
                        "effectiveDateTime": "2026-03-10T09:00:00Z",
                        "valueQuantity": {"value": 95, "unit": "mg/dL"},
                        "identifier": [{"value": "ACC-001"}],
                    }
                },
            ],
        }

        result = process_fhir_bundle(bundle, teams["lakewood"])
        assert result["patients"] == 1
        assert result["observations"] == 1
        assert Patient.objects.filter(mrn="TEST-001").exists()
        assert LabResult.objects.filter(accession_number="ACC-001").exists()
