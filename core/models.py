from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def generate_test_subject_id():
    """Generate a human-readable, unique LIMS patient identifier."""
    return f"LIMS-{uuid4().hex[:8].upper()}"


class Patient(models.Model):
    id = models.BigAutoField(primary_key=True)
    test_subject_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        default=generate_test_subject_id,
    )
    national_id = models.CharField(max_length=30, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=120)
    middle = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120)
    # Kept as DateTimeField for now to avoid silently changing the database schema.
    # A later planned migration can convert this to DateField if desired.
    date_of_birth = models.DateTimeField(blank=True, null=True)
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
        ("U", "Unknown"),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="U")
    blood_group = models.CharField(max_length=3, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=120, blank=True, null=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["-registration_date"]
        indexes = [
            models.Index(fields=["test_subject_id"]),
            models.Index(fields=["national_id"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.test_subject_id:
            self.test_subject_id = generate_test_subject_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.test_subject_id} - {self.first_name} {self.last_name}"


class Test(models.Model):
    id = models.BigAutoField(primary_key=True)
    test_code = models.CharField(
        max_length=30,
        unique=True,
        help_text="Unique test code, e.g. CBC, GLU, CHOL",
    )
    test_name = models.CharField(
        max_length=150,
        help_text="Full name of the test (e.g. Complete Blood Count)",
    )
    department = models.CharField(
        max_length=100,
        help_text="Department (e.g. Hematology, Biochemistry, Immunology)",
    )
    sample_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="e.g. Blood, Serum, Urine",
    )
    unit = models.CharField(max_length=30, blank=True, null=True)
    reference_range = models.CharField(max_length=120, blank=True, null=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    turnaround_time_hours = models.PositiveBigIntegerField(default=24)
    active = models.BooleanField(default=True)
    instructions = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Tests"
        ordering = ["department", "test_name"]
        indexes = [
            models.Index(fields=["test_code"]),
            models.Index(fields=["test_name"]),
        ]

    def __str__(self):
        return f"{self.test_code} - {self.test_name}"


STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
]


class TestParameter(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="parameters")
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=50)
    min_value = models.FloatField()
    max_value = models.FloatField()

    def clean(self):
        if self.min_value > self.max_value:
            raise ValidationError({"max_value": "Maximum value must be at least the minimum value."})

    def __str__(self):
        return f"{self.test.test_name} - {self.name}"


class LabOrder(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("approved", "Approved"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    test = models.ForeignKey(Test, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def approve(self):
        results = self.results.all()
        expected_count = self.test.parameters.count()
        if results.count() < expected_count:
            raise ValidationError("Enter results for all test parameters before approval.")

        self.status = "approved"
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_at"])


class ParameterResult(models.Model):
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="results")
    parameter = models.ForeignKey(TestParameter, on_delete=models.PROTECT)
    value = models.FloatField()
    flag = models.CharField(max_length=10, blank=True)

    def clean(self):
        if self.parameter_id and self.order_id:
            if self.parameter.test_id != self.order.test_id:
                raise ValidationError("The parameter must belong to the test assigned to this order.")

    def save(self, *args, **kwargs):
        if self.parameter_id:
            if self.value < self.parameter.min_value:
                self.flag = "Low"
            elif self.value > self.parameter.max_value:
                self.flag = "High"
            else:
                self.flag = "Normal"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parameter.name} - {self.value}"


class PatientTest(models.Model):
    id = models.BigAutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="patient_tests")
    test = models.ForeignKey(Test, on_delete=models.PROTECT, related_name="test_records")
    sample_identifier = models.CharField(max_length=80, blank=True, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    # Kept as auto_now_add for schema compatibility; this should be reviewed separately.
    result_date = models.DateTimeField(auto_now_add=True)
    result_valu = models.CharField(max_length=200, blank=True, null=True)
    result_text = models.TextField(blank=True, null=True)
    performed_by = models.CharField(max_length=120, blank=True, null=True)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    price_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        verbose_name = "Patient Test"
        verbose_name_plural = "Patient Tests"
        ordering = ["-request_date"]
        indexes = [
            models.Index(fields=["patient", "test"]),
            models.Index(fields=["request_date"]),
        ]

    def save(self, *args, **kwargs):
        if self.test_id and self.price_snapshot is None:
            self.price_snapshot = self.test.price

        if self.price_snapshot is not None:
            discount = self.discount_percent or Decimal("0.00")
            discount_amount = self.price_snapshot * (discount / Decimal("100.00"))
            self.total_price = (self.price_snapshot - discount_amount).quantize(Decimal("0.01"))
        else:
            self.total_price = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} - {self.test.test_code}"


class TestResult(models.Model):
    patienttest = models.OneToOneField(PatientTest, on_delete=models.CASCADE)
    wbc = models.FloatField("WBC", null=True, blank=True)
    rbc = models.FloatField("RBC", null=True, blank=True)
    hemoglobin = models.FloatField("Hemoglobin", null=True, blank=True)
    hematocrit = models.FloatField("Hematocrit", null=True, blank=True)
    platelets = models.FloatField("Platelets", null=True, blank=True)
    result_valu = models.CharField(max_length=100, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("approved", "Approved"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_results",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_results",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("approve_testresult", "Can approve test result")]

    def __str__(self):
        return f"Result for {self.patienttest}"


class Profile(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("doctor", "Doctor"),
        ("technician", "Technician"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action}"
