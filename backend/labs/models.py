from django.db import models


class BaseModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Team(BaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Patient(BaseModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="patients")
    mrn = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    patient_data = models.JSONField(default=dict)

    class Meta:
        unique_together = ["team", "mrn"]

    def __str__(self):
        return f"{self.name} ({self.mrn})"


class LabResult(BaseModel):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="lab_results"
    )
    accession_number = models.CharField(max_length=100)
    test_name = models.CharField(max_length=255)
    test_code = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    unit = models.CharField(max_length=50, blank=True)
    effective_date = models.DateTimeField()
    observation_data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.test_name}: {self.value} {self.unit}"


class PatientAllergy(BaseModel):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="allergies"
    )
    substance = models.CharField(max_length=255)
    criticality = models.CharField(max_length=50, null=True, blank=True)
    allergy_data = models.JSONField(default=dict)

    class Meta:
        verbose_name_plural = "patient allergies"

    def __str__(self):
        return f"{self.substance} ({self.criticality})"
