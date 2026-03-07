from django.db import models
from uuid import uuid4
from django.contrib.auth.models import User

def generste_test_subject_id():
    return f"LIMS-{uuid4().hex[:8].upper()}"

class Patient(models.Model):
    id = models.BigAutoField(primary_key=True)
    test_subject_id = models.CharField(max_length=50, unique=True, blank=True)
    national_id = models.CharField(max_length=30, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=120)
    middle = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120)
    date_of_birth = models.DateTimeField(blank=True, null=True)
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other'), ('U', 'Unknown')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
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
        ordering = ['-registration_date']
        indexes = [
            models.Index(fields=['test_subject_id']), 
            models.Index(fields=['national_id']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    def __str__(self):
        return f"{self.test_subject_id} - {self.first_name} {self.last_name}"
    

from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator
class Test(models.Model):
        id = models.BigAutoField(primary_key=True)
        test_code = models.CharField(max_length=30, unique=True, help_text="Unique test code, e.g, CBC, GLU, CHOL")
        test_name = models.CharField(max_length=150, help_text="Full name of the test (e.g. Complete,Blood Count)")
        department = models.CharField(max_length=100, help_text="Department(e.g, Hematologe, Biochemistry, Immunology)")
        sample_type = models.CharField(max_length=50, blank=True, null=True, help_text="e.g, Boold, Serum, Urine")
        unit = models.CharField(max_length=30, blank=True, null=True, help_text="Measurement unit (e.g. mg/dL, IU/L)")
        reference_range = models.CharField(max_length=120, blank=True, null=True, help_text="Example: 4.5 - 10.0 *10^9/L")
        price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))], help_text="Cost of the test")
        turnaround_time_hours = models.PositiveBigIntegerField(default=24, help_text="Expected time to complete (in hours)")
        active = models.BooleanField(default=True, help_text="Set to False to deactivativate the test")
        instructions = models.TextField(blank=True, null=True)
        created_at = models.DateTimeField(auto_now_add=True)
        last_update = models.DateTimeField(auto_now=True)

        class Meta:
            verbose_name = "Test"
            verbose_name_plural = "Tests"
            ordering = ['department', 'test_name']
            indexes = [
                models.Index(fields=['test_code']),
                models.Index(fields=['test_name']),
         ]
        def __str__(self):
                return f"{self.test_code} - {self.test_name}"
        
        
from decimal import Decimal 
from django.core.validators import MinLengthValidator, MaxValueValidator
STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
]
class TestParameter(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=50)
    min_value = models.FloatField()
    max_value = models.FloatField()


    def __str__(self):
        return f"{self.test.test_name} - {self.name}"
from django.core.exceptions import ValidationError

class LabOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ]

    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def approve(self):
        # تأكد كل النتائج مدخلة
        results = self.results.all()
        for r in results:
            if r.value == 0:
                raise ValidationError("All parameter values must be entered before approval.")

        self.status = 'approved'
        from django.utils import timezone
        self.approved_at = timezone.now()
        self.save()
    
class ParameterResult(models.Model):
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='results')
    parameter = models.ForeignKey(TestParameter, on_delete=models.CASCADE)
    value = models.FloatField()
    flag = models.CharField(max_length=10, blank=True)

    def save(self, *args, **kwargs):
        # تحديد الحالة High / Low / Normal
        if self.value < self.parameter.min_value:
            self.flag = 'Low'
        elif self.value > self.parameter.max_value:
            self.flag = 'High'
        else:
            self.flag = 'Normal'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parameter.name} - {self.value}"

class PatientTest(models.Model):
     id = models.BigAutoField(primary_key=True)
     patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_tests')
     test = models.ForeignKey(Test, on_delete=models.PROTECT, related_name='test_records')
     sample_identifier = models.CharField(max_length=80, blank=True, null=True, help_text="Sample ID if lab uses one")
     request_date = models.DateTimeField(auto_now_add=True)
     result_date = models.DateTimeField(auto_now_add=True)
     result_valu = models.CharField(max_length=200, blank=True, null=True)
     result_text = models.TextField(blank=True, null=True)
     performed_by = models.CharField(max_length=120, blank=True, null=True)
     discount_percent = models.DecimalField(max_digits=5, decimal_places=2, 
    default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00')),
     MaxValueValidator(Decimal('100.00'))], help_text="Discount as percent (0-100)")
     price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, 
    validators=[MinLengthValidator(Decimal('0.00'))], help_text="Price at time request (copied from Test.price)")
     total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Computed price after discount")
     created_at = models.DateTimeField(auto_now_add=True)
     status = models.CharField( max_length=20, choices=STATUS_CHOICES, default='pending')
     class Meta:
          verbose_name = "PatientTest"
          verbose_name_plural = "PatientTest"
          ordering = ['-request_date']
          indexes = models.Index(fields=['patient', 'test']), models.Index(fields=['request_date'])

     def save(self, *args, **kwargs):
         if not self.price_snapshot and self.test:
               self.price_snapshot = self.test.price
         if self.price_snapshot is not None:
               discount_amount = (self.price_snapshot * (self.discount_percent / Decimal('100.00')))
               self.total_price = (self.price_snapshot - discount_amount).quantize(Decimal('0.01'))
               super().save(*args, **kwargs)

     def __str__(self):
               return f"{self.patient} - {self.test.test_code}"
     
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
class TestResult(models.Model):
    patienttest = models.OneToOneField( PatientTest,on_delete=models.CASCADE )
    wbc = models.FloatField("WBC", null=True, blank=True)
    rbc = models.FloatField("RBC", null=True, blank=True)
    hemoglobin = models.FloatField("Hemoglobin", null=True, blank=True)
    hematocrit = models.FloatField("Hematocrit", null=True, blank=True)
    platelets = models.FloatField("Platelets", null=True, blank=True)
    result_valu = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_results'
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_results'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
         permissions =[("approve_testresult", "Can approve testresult"),]

    def __str__(self):
        return f"Result for {self.patienttest}"
    
from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('technician', 'Technician'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action}"