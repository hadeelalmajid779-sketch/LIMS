# core/forms.py
from django import forms
from .models import Patient, Test, PatientTest
from decimal import Decimal
from django import forms
from .models import Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['test_subject_id','national_id','first_name','middle','last_name','date_of_birth',
                  'gender','blood_group','phone','email','address','emergency_contact', 'notes'
        ]
class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = [
            'test_code', 'test_name', 'department', 'sample_type',
            'unit', 'reference_range', 'price', 'turnaround_time_hours',
            'instructions', 'active'
        ]
        widgets = {
            'instructions': forms.Textarea(attrs={'rows':3}),
            'reference_range': forms.Textarea(attrs={'rows':2}),
            'price': forms.NumberInput(attrs={'step':'0.01'}),
            'turnaround_time_hours': forms.NumberInput(attrs={'min':0}),
        }

class PatientTestForm(forms.ModelForm):
    class Meta:
        model = PatientTest
        fields = ['patient','test','sample_identifier','result_valu','result_text','performed_by','discount_percent']
        widgets = {
            'patient': forms.Select(attrs={'class':'form-control'}),
            'test': forms.Select(attrs={'class':'form-control'}),
            'sample_identifier': forms.TextInput(attrs={'class':'form-control'}),
            'result_valu': forms.TextInput(attrs={'class':'form-control'}),
            'result_text': forms.Textarea(attrs={'rows':2,'class':'form-control'}),
            'performed_by': forms.TextInput(attrs={'class':'form-control'}),
            'discount_percent': forms.NumberInput(attrs={'step':'0.01','class':'form-control'}),
        }
    def clean_discount_percent(self):
        dp = self.cleaned_data.get('discount_percent') or Decimal('0.00')
        if dp < 0 or dp > 100:
            raise forms.ValidationError("Discount must be between 0 and 100")
        return dp
    
from .models import TestResult

class TestResultForm(forms.ModelForm):
    class Meta:
        model = TestResult
        fields = ['result_valu', 'unit', 'reference_range', 'wbc','rbc','hemoglobin','hematocrit','platelets']
