"""Utilities for parsing FHIR R4 resources into local models."""
from datetime import datetime

from .models import LabResult, Patient, PatientAllergy, Team


def process_fhir_bundle(bundle_data, team):
    """Process a FHIR R4 Bundle and create local records."""
    results = {"patients": 0, "observations": 0, "allergies": 0, "errors": []}

    for entry in bundle_data.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        try:
            if resource_type == "Patient":
                _process_patient(resource, team)
                results["patients"] += 1
            elif resource_type == "Observation":
                _process_observation(resource, team)
                results["observations"] += 1
            elif resource_type == "AllergyIntolerance":
                _process_allergy(resource, team)
                results["allergies"] += 1
        except Exception as e:
            results["errors"].append(f"Error processing {resource_type}: {e}")

    return results


def _process_patient(resource, team):
    """Create or update a Patient from a FHIR Patient resource."""
    identifiers = resource.get("identifier", [])
    mrn = None
    for ident in identifiers:
        if ident.get("type", {}).get("coding", [{}])[0].get("code") == "MR":
            mrn = ident["value"]
            break

    if not mrn:
        mrn = identifiers[0]["value"] if identifiers else resource.get("id", "")

    name_parts = resource.get("name", [{}])[0]
    family = name_parts.get("family", "")
    given = " ".join(name_parts.get("given", []))
    full_name = f"{family}, {given}".strip(", ")

    patient, _ = Patient.objects.update_or_create(
        team=team,
        mrn=mrn,
        defaults={
            "name": full_name,
            "date_of_birth": resource.get("birthDate", "2000-01-01"),
            "patient_data": resource,
        },
    )
    return patient


def _process_observation(resource, team):
    """Create a LabResult from a FHIR Observation resource."""
    subject_ref = resource.get("subject", {}).get("reference", "")
    patient_mrn = subject_ref.split("/")[-1] if "/" in subject_ref else subject_ref

    patient = Patient.objects.filter(team=team, mrn=patient_mrn).first()
    if not patient:
        raise ValueError(f"Patient not found: {patient_mrn}")

    code_info = resource.get("code", {}).get("coding", [{}])[0]
    value_qty = resource.get("valueQuantity", {})
    identifiers = resource.get("identifier", [])
    accession = identifiers[0]["value"] if identifiers else resource.get("id", "")

    effective_dt = resource.get("effectiveDateTime")
    if not effective_dt:
        period = resource.get("effectivePeriod", {})
        effective_dt = period.get("start")

    if effective_dt and not effective_dt.endswith("Z") and "+" not in effective_dt:
        effective_dt += "Z"

    LabResult.objects.update_or_create(
        accession_number=accession,
        defaults={
            "patient": patient,
            "test_name": code_info.get("display", "Unknown"),
            "test_code": code_info.get("code", ""),
            "value": str(value_qty.get("value", "")),
            "unit": value_qty.get("unit", ""),
            "effective_date": effective_dt,
            "observation_data": resource,
        },
    )


def _process_allergy(resource, team):
    """Create a PatientAllergy from a FHIR AllergyIntolerance resource."""
    subject_ref = resource.get("patient", {}).get("reference", "")
    patient_mrn = subject_ref.split("/")[-1] if "/" in subject_ref else subject_ref

    patient = Patient.objects.filter(team=team, mrn=patient_mrn).first()
    if not patient:
        raise ValueError(f"Patient not found: {patient_mrn}")

    code_info = resource.get("code", {}).get("coding", [{}])[0]
    substance = code_info.get("display", "Unknown substance")
    criticality = resource.get("criticality")

    PatientAllergy.objects.update_or_create(
        patient=patient,
        substance=substance,
        defaults={
            "criticality": criticality,
            "allergy_data": resource,
        },
    )
