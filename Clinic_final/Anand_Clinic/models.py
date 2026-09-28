from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from django.db import models
from django.contrib.auth.models import User
import uuid
# Create your models here.

class Profile(models.Model):
    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    whatsapp = models.CharField(max_length=15)
    country_code = models.CharField(max_length=5, default='91')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
DOCTOR_CHOICES = [
    ('dr_1', 'Dr. Ami Bhatt'),
    ('dr_2', 'Dr. Kaushal Bhatt'),
]
GENDER = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other')
]

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

class Patient(models.Model):
    case_no = models.AutoField(primary_key=True)
    case = models.CharField(max_length=20, null=True, blank=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    phone_no = models.CharField(max_length=10)
    doctor = models.CharField(max_length=50, choices=DOCTOR_CHOICES)
    gender = models.CharField(max_length=50, choices=GENDER)
    address = models.CharField(max_length=255, null=True, blank=True)
    # store appointment as a datetime so we can record exact creation time
    appointment_date = models.DateTimeField(default=timezone.now)
    last_visited = models.DateTimeField(null=True, blank=True)
    # Track the lower margin of the last printed prescription on current page
    page_lower_margin_mm = models.FloatField(default=0, help_text="Lower margin position of last prescription on current page for this patient")

    def __str__(self):
        # Use the human-readable doctor label; avoid referencing the bound method itself
        doctor_label = self.get_doctor_display()
        return (
            f'Patient Case: {self.case}, Case No: {self.case_no}, Name: {self.name}, '
            f'Age: {self.age}, Gender: {self.gender}, Phone: {self.phone_no}, '
            f'Address: {self.address}, Doctor: {doctor_label}'
        )


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    visit_datetime = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_datetime']

    def __str__(self):
        return f"Visit for {getattr(self.patient, 'name', self.patient)} @ {self.visit_datetime:%Y-%m-%d %H:%M}"


# Pharmacy Models

MEDICINE_TYPE_CHOICES = [
    ('tablet', 'Tablet'),
    ('capsule', 'Capsule'),
    ('syrup', 'Syrup'),
    ('injection', 'Injection'),
    ('ointment', 'Ointment'),
    ('drops', 'Drops'),
    ('other', 'Other'),
]

class Medicine(models.Model):
    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200, blank=True, null=True)
    medicine_type = models.CharField(max_length=50, choices=MEDICINE_TYPE_CHOICES, default='tablet')
    manufacturer = models.CharField(max_length=200, blank=True, null=True)
    batch_number = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reorder_level = models.IntegerField(default=10, help_text="Minimum stock level before reordering")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.medicine_type}) - Stock: {self.stock_quantity}"

    def is_low_stock(self):
        """Check if medicine stock is below reorder level"""
        return self.stock_quantity <= self.reorder_level

    def is_expired(self):
        """Check if medicine has expired"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False


    
class StockTransaction(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='transactions')
    change = models.IntegerField()  # positive = stock added, negative = stock removed
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.medicine.name}: {self.change} @ {self.created_at:%Y-%m-%d %H:%M}"


class Prescription(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='generated_prescriptions')
    visit = models.ForeignKey('Visit', on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    case_number = models.IntegerField(default=0)
    case = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    prescribed_by_ami = models.BooleanField(default=False)
    prescribed_by_kaushal = models.BooleanField(default=False)
    language = models.CharField(max_length=5, choices=[('en','English'),('gu','Gujarati')], default='en')
    printed_height_mm = models.FloatField(default=0, help_text="Height of prescription when printed in mm")
    top_margin_mm = models.FloatField(default=0, help_text="Top margin position for this prescription on the page in mm")

    def calculate_printed_height_mm(self):
        """
        Calculate the printed height of this prescription in millimetres.
        Uses assumptions: font-size 14px, line-height 1.5 during print.
        Returns height in mm.
        """
        # Count total lines from first day and next day instructions
        total_lines = 0
        
        # Add header lines (standard for all prescriptions)
        total_lines += 4  # title, to, patient case, intro
        total_lines += 2  # Date line + spacing
        total_lines += 1  # blank line
        total_lines += 1  # "First day" header
        
        # Add first day instructions
        for fd in self.first_day_instructions.all():
            total_lines += 1  # one line per instruction
        
        total_lines += 1  # blank line
        total_lines += 1  # "From Next day onwards" header
        
        # Add next day instructions
        for nd in self.next_day_instructions.all():
            total_lines += 1  # one line per instruction
        
        total_lines += 1  # blank line
        total_lines += 1  # doctor names line
        
        # Convert lines to mm
        # 14px * 1.5 line-height = 21px per line
        # 1 px = 0.264583 mm (at 96 DPI), so 21px = 5.556 mm
        px_to_mm = 25.4 / 96.0
        per_line_mm = 14 * 1.5 * px_to_mm
        
        printed_height_mm = total_lines * per_line_mm
        
        # Add padding: 10px top + 10px bottom = 20px
        padding_mm = 20 * px_to_mm
        
        return printed_height_mm + padding_mm

    def save(self, *args, **kwargs):
        """Override save to automatically calculate and store printed height."""
        # Only calculate if this is an update (pk exists) or if already has related instructions
        if self.pk:
            # This is an update, safe to calculate
            self.printed_height_mm = self.calculate_printed_height_mm()
        # For new instances without pk, skip calculation - it will be done after instructions are added
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Prescription for {getattr(self.patient, 'name', str(self.patient))} ('Patient Case: {self.case})(Case No. {self.case_number})"

class PersonalNote(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_notes')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='personal_notes')
    note = models.TextField(blank=True)
    image = models.ImageField(upload_to='personal_notes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {getattr(self.patient, 'name', str(self.patient))} by {getattr(self.doctor, 'username', self.doctor_id)}"


class PersonalNoteImage(models.Model):
    note = models.ForeignKey(PersonalNote, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='personal_notes/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for note {self.note_id}"


class FirstDayInstruction(models.Model):
    SIZE_SMALL = 'Small'
    SIZE_MEDIUM = 'Medium'
    SIZE_LARGE = 'Large'
    SIZE_CHOICES = [
        (SIZE_SMALL, 'Small'),
        (SIZE_MEDIUM, 'Medium'),
        (SIZE_LARGE, 'Large'),
    ]

    TIME_DAY = 'Day'
    TIME_MORNING = 'Morning'
    TIME_NIGHT = 'Night'
    TIME_CHOICES = [
        (TIME_DAY, 'Day'),
        (TIME_MORNING, 'Morning'),
        (TIME_NIGHT, 'Night'),
    ]

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='first_day_instructions')
    size_of_bottle = models.CharField(max_length=10, choices=SIZE_CHOICES)
    label = models.CharField(max_length=100)
    no_of_pill = models.CharField(max_length=20)
    time_of_day = models.CharField(max_length=100)
    special_instruction = models.TextField(blank=True)

    def __str__(self):
        return f"{self.size_of_bottle} bottle '{self.label}' {self.no_of_pill} at {self.time_of_day}"


class NextDayInstruction(models.Model):
    DOSE_ONE = 'one'
    DOSE_TWO = 'two'
    DOSE_THREE = 'three'
    DOSE_FOUR = 'four'
    DOSE_FIVE = 'five'
    DOSE_CHOICES = [
        (DOSE_ONE, 'one'),
        (DOSE_TWO, 'two'),
        (DOSE_THREE, 'three'),
        (DOSE_FOUR, 'four'),
        (DOSE_FIVE, 'five'),
    ]

    TIME_DAY = 'Day'
    TIME_MORNING = 'Morning'
    TIME_NIGHT = 'Night'
    TIME_CHOICES = [
        (TIME_DAY, 'Day'),
        (TIME_MORNING, 'Morning'),
        (TIME_NIGHT, 'Night'),
    ]

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='next_day_instructions')
    bottle_no = models.CharField(max_length=50)
    no_of_pill = models.CharField(max_length=20)
    dose = models.CharField(max_length=10, choices=DOSE_CHOICES, blank=True, null=True)
    time_of_day = models.CharField(max_length=100)
    special_instruction = models.TextField(blank=True)

    def __str__(self):
        return f"Bottle {self.bottle_no} {self.no_of_pill} {self.dose} a {self.time_of_day}"

# my code for follow up...
class FollowUp(models.Model):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_COMPLETED = 'completed'
    STATUS_MISSED = 'missed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_MISSED, 'Missed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='followups')
    scheduled_date = models.DateTimeField(help_text="When the follow-up is scheduled")
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    outcome = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    reminder_sent = models.BooleanField(default=False)
    # Optional check-in fields stored on the follow-up for quick reference
    checkin_time = models.DateTimeField(null=True, blank=True, help_text='When the patient checked in')
    CHECKIN_STATUS_CHOICES = [
        ('early', 'Early'),
        ('on_time', 'On Time'),
        ('late', 'Late'),
    ]
    checkin_status = models.CharField(max_length=20, choices=CHECKIN_STATUS_CHOICES, null=True, blank=True)
    checkin_minutes_difference = models.IntegerField(null=True, blank=True, help_text='Signed minutes difference: checkin - scheduled')
    checkin_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='checkins_done')

    class Meta:
        ordering = ['-scheduled_date']
        verbose_name = 'Follow up'
        verbose_name_plural = 'Follow ups'

    def __str__(self):
        return f"FollowUp for {getattr(self.patient, 'name', str(self.patient))} on {self.scheduled_date:%Y-%m-%d %H:%M} ({self.status})"

    def clean(self):
        # Validate scheduled_date is in the future (only for scheduled status)
        if self.status == self.STATUS_SCHEDULED:
            if self.scheduled_date and self.scheduled_date < timezone.now():
                raise ValidationError({'scheduled_date': 'Scheduled date must be in the future.'})

            # Enforce only one active scheduled follow-up per patient
            qs = FollowUp.objects.filter(patient=self.patient, status=self.STATUS_SCHEDULED)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('There is already a scheduled follow-up for this patient.')

    def save(self, *args, **kwargs):
        # Run full_clean to enforce the above validations
        self.full_clean()
        super().save(*args, **kwargs)


# Check-in model to track patient arrival relative to a scheduled follow-up
class CheckIn(models.Model):
    STATUS_EARLY = 'early'
    STATUS_ON_TIME = 'on_time'
    STATUS_LATE = 'late'
    STATUS_CHOICES = [
        (STATUS_EARLY, 'Early'),
        (STATUS_ON_TIME, 'On Time'),
        (STATUS_LATE, 'Late'),
    ]

    followup = models.ForeignKey(FollowUp, on_delete=models.CASCADE, related_name='checkins')
    checkin_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ON_TIME)
    minutes_difference = models.IntegerField(help_text='Signed minutes difference: checkin - scheduled', default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-checkin_time']

    def __str__(self):
        return f"CheckIn for {getattr(self.followup.patient, 'name', str(self.followup.patient))} at {self.checkin_time:%Y-%m-%d %H:%M} ({self.status})"
