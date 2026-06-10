from django.urls import path

from . import views

urlpatterns = [
    path(
        "teams/<slug:slug>/patients/",
        views.PatientListView.as_view(),
        name="patient-list",
    ),
    path(
        "teams/<slug:slug>/patients/<int:pk>/",
        views.PatientDetailView.as_view(),
        name="patient-detail",
    ),
    path(
        "teams/<slug:slug>/patients/<int:patient_pk>/lab-results/",
        views.LabResultListView.as_view(),
        name="lab-result-list",
    ),
]
