from rest_framework import generics

from .models import LabResult, Patient
from .serializers import (
    LabResultSerializer,
    PatientDetailSerializer,
    PatientListSerializer,
)


class PatientListView(generics.ListAPIView):
    serializer_class = PatientListSerializer

    def get_queryset(self):
        return Patient.objects.filter(team__slug=self.kwargs["slug"]).order_by("name")


class PatientDetailView(generics.RetrieveAPIView):
    serializer_class = PatientDetailSerializer

    def get_queryset(self):
        return Patient.objects.filter(team__slug=self.kwargs["slug"])


class LabResultListView(generics.ListAPIView):
    serializer_class = LabResultSerializer

    def get_queryset(self):
        return LabResult.objects.filter(
            patient_id=self.kwargs["patient_pk"],
            patient__team__slug=self.kwargs["slug"],
        ).order_by("-effective_date")
