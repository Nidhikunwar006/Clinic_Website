from django import forms 
from django.core.validators import RegexValidator
import re
from .models import Medicine, Patient

class ForgotPasswordForm(forms.Form):
    # Simplified forgot-password form: always ask for username.
    username = forms.CharField(
        max_length=150,
        label="Username",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Enter your username"})
    )
    whatsapp = forms.CharField(
        max_length=15,
        label="Mobile Number",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter registered WhatsApp number"})
    )


class ResetPasswordForm(forms.Form):
    new_username = forms.CharField(
        max_length=150,
        required=False,
        label="New Username",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter new username",
            "class": "input-field"
        })
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "New Password"}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"}),
        label="Confirm Password"
    )

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "New Password"}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"}),
        label="Confirm Password"
    )
    
class PrescriptionGeneratorForm(forms.Form):
    patient = forms.ModelChoiceField(queryset=Patient.objects.all())
    case_number = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required=False)
    instruction_type = forms.ChoiceField(choices=[('first', 'First Day Instructions'), ('next', 'From Next Day Onwards')])

DOCTOR_CHOICES = [
    ('dr_1','Dr. Ami Bhatt'),
    ('dr_2','Dr. Kaushal Bhatt'),
]
GENDER = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other')]

MEDICINE_TYPE_CHOICES = [
    ('tablet', 'Tablet'),
    ('capsule', 'Capsule'),
    ('syrup', 'Syrup'),
    ('injection', 'Injection'),
    ('ointment', 'Ointment'),
    ('drops', 'Drops'),
    ('other', 'Other'),
]


class PatientForm(forms.ModelForm):
        case = forms.CharField()
        name = forms.CharField()
        # enforce integer age and non-negative
        age = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={'min': '0', 'step': '1'}))
        gender = forms.ChoiceField(choices=GENDER)
        address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
        # phone stored on model as integer; must be exactly 10 digits
        phone_no = forms.CharField(max_length=10,validators=[RegexValidator(r'^\d{10}$','Phone number must be exactly 10 digits (numbers only).')],widget=forms.TextInput(attrs={'inputmode': 'numeric','maxlength': '10','pattern': r'\d{10}',}))

        doctor = forms.ChoiceField(choices=DOCTOR_CHOICES)

        class Meta:
            model = Patient
            fields = ['case', 'name', 'gender', 'age', 'phone_no', 'address', 'doctor']
        
        def clean_case(self):
                value = (self.cleaned_data.get('case') or '').strip()
                if not value:
                    raise forms.ValidationError('Enter valid case')
                return value
        
        def clean(self):
                cleaned = super().clean()
                case_val = (cleaned.get('case') or '').strip()
                name_val = (cleaned.get('name') or '').strip()
                if case_val:
                    try:
                        existing = Patient.objects.filter(case__iexact=case_val).first()
                        if existing and name_val and name_val.strip().lower() != str(existing.name).strip().lower():
                            self.add_error('case', 'Enter valid case')
                    except Exception:
                        pass
                return cleaned
        
        def clean_phone_no(self):
                raw = self.cleaned_data.get('phone_no', '') or ''
                # remove any non-digit characters just in case
                digits = re.sub(r'\D', '', raw)
                if not digits:
                    raise forms.ValidationError('Enter a phone number with digits only.')
                if len(digits) != 10:
                    raise forms.ValidationError('Phone number must be exactly 10 digits.')
                # convert to int for model's IntegerField (preserve numeric storage)
                try:
                    return int(digits)
                except ValueError:
                    raise forms.ValidationError('Invalid phone number.')


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'generic_name', 'medicine_type', 'manufacturer', 'batch_number', 
                  'expiry_date', 'stock_quantity', 'unit_price', 'reorder_level', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine Name'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Generic Name'}),
            'medicine_type': forms.Select(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Batch Number'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
        }


class SimpleMedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'stock_quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine Name'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
