from rest_framework import serializers

from .models import LabResult, Patient, PatientAllergy


class LabResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResult
        fields = [
            "id",
            "accession_number",
            "test_name",
            "test_code",
            "value",
            "unit",
            "effective_date",
            "observation_data",
        ]


class PatientAllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAllergy
        fields = ["id", "substance", "criticality", "allergy_data"]


class PatientListSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Patient
        fields = ["id", "mrn", "name", "date_of_birth", "team_name"]


class PatientDetailSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    lab_results = LabResultSerializer(many=True, read_only=True)
    allergies = PatientAllergySerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "mrn",
            "name",
            "date_of_birth",
            "team_name",
            "allergies",
            "lab_results",
        ]
