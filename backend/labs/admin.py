from django.contrib import admin

from .models import LabResult, Patient, PatientAllergy, Team

admin.site.register(Team)
admin.site.register(Patient)
admin.site.register(LabResult)
admin.site.register(PatientAllergy)
