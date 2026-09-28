import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Clinic.settings')
import django
django.setup()
from Anand_Clinic.models import Patient, Prescription

MARGIN_MM = 20
MARGIN_GAP_MM = 10
A4_HEIGHT_MM = 297

patient = Patient.objects.get(case_no=9999)
print('Patient before:', patient.page_lower_margin_mm)

# Create 6th prescription
presc = Prescription.objects.create(
    patient=patient,
    case='TEST-6',
    case_number=6,
    prescribed_by_ami=True,
    language='en'
)
# choose a height that would normally fit or not; use 60
presc.printed_height_mm = 60.0

proposed_top_abs = patient.page_lower_margin_mm + MARGIN_GAP_MM
proposed_bottom_abs = proposed_top_abs + presc.printed_height_mm

if proposed_bottom_abs > A4_HEIGHT_MM:
    presc.top_margin_mm = MARGIN_GAP_MM
    patient.page_lower_margin_mm = MARGIN_MM + presc.top_margin_mm + presc.printed_height_mm
else:
    presc.top_margin_mm = max(MARGIN_GAP_MM, proposed_top_abs - MARGIN_MM)
    patient.page_lower_margin_mm = MARGIN_MM + presc.top_margin_mm + presc.printed_height_mm

presc.save(update_fields=['printed_height_mm','top_margin_mm'])
patient.save(update_fields=['page_lower_margin_mm'])

print('Added TEST-6, top_rel=', presc.top_margin_mm, 'patient.lower_abs=', patient.page_lower_margin_mm)

# Print all TEST prescriptions
for p in Prescription.objects.filter(case__startswith='TEST').order_by('case_number'):
    abs_top = p.top_margin_mm + MARGIN_MM
    bottom = abs_top + p.printed_height_mm
    print(p.case, 'top_rel=', p.top_margin_mm, 'abs_top=', abs_top, 'height=', p.printed_height_mm, 'bottom=', bottom)
