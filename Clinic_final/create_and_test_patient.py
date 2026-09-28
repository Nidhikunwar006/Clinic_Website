import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Clinic.settings')
import django
django.setup()
from Anand_Clinic.models import Patient, Prescription
from django.utils import timezone

MARGIN_MM = 20
MARGIN_GAP_MM = 10
A4_HEIGHT_MM = 297

# Create test patient
patient, created = Patient.objects.get_or_create(
    case_no=8888,
    defaults={
        'name': 'Auto Test Patient',
        'age': 40,
        'phone_no': '0000000000',
        'doctor': 'dr_test',
        'gender': 'male',
    }
)
if not created:
    # reset page lower margin for clean test
    patient.page_lower_margin_mm = MARGIN_MM
    patient.save(update_fields=['page_lower_margin_mm'])

print('Patient', patient.case_no, 'created=', created, 'starting page_lower_margin_mm=', patient.page_lower_margin_mm)

# Prescription heights to test (mm)
heights = [100, 80, 100, 60, 70, 50]

created_prescs = []
for i, h in enumerate(heights, start=1):
    presc = Prescription.objects.create(
        patient=patient,
        case=f'AUTO-{i}',
        case_number=i,
        prescribed_by_ami=True,
        language='en'
    )
    presc.printed_height_mm = float(h)

    # compute previous lower using most recent previous prescription for this patient
    prev = Prescription.objects.filter(patient=patient).exclude(pk=presc.pk).order_by('-created_at').first()
    if prev:
        prev_abs_top = MARGIN_MM + prev.top_margin_mm
        prev_lower_abs = prev_abs_top + prev.printed_height_mm
    else:
        prev_lower_abs = MARGIN_MM

    proposed_top_abs = prev_lower_abs + MARGIN_GAP_MM
    proposed_bottom_abs = proposed_top_abs + presc.printed_height_mm

    if proposed_bottom_abs > A4_HEIGHT_MM:
        # move to new page
        presc.top_margin_mm = MARGIN_GAP_MM
        patient.page_lower_margin_mm = MARGIN_MM + presc.top_margin_mm + presc.printed_height_mm
        reason = 'moved_to_new_page'
    else:
        presc.top_margin_mm = max(MARGIN_GAP_MM, proposed_top_abs - MARGIN_MM)
        patient.page_lower_margin_mm = MARGIN_MM + presc.top_margin_mm + presc.printed_height_mm
        reason = 'fits_on_current_page'

    presc.save(update_fields=['printed_height_mm','top_margin_mm'])
    patient.save(update_fields=['page_lower_margin_mm'])
    created_prescs.append((presc.case, presc.top_margin_mm, presc.printed_height_mm, reason))

# Print summary
print('\nSummary for new test patient (case_no=8888):')
print('MARGIN_MM=', MARGIN_MM, 'GAP=', MARGIN_GAP_MM, 'A4=', A4_HEIGHT_MM)
for case, top_rel, height, reason in created_prescs:
    abs_top = top_rel + MARGIN_MM
    bottom = abs_top + height
    print(f"{case}: top_rel={top_rel}mm abs_top={abs_top}mm height={height}mm bottom={bottom}mm -> {reason}")

print('\nFinal patient.page_lower_margin_mm =', patient.page_lower_margin_mm)
