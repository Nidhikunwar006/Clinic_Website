import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Clinic.settings')
import django
django.setup()
from Anand_Clinic.models import Patient, Prescription

MARGIN_MM = 20
MARGIN_GAP_MM = 10
A4_HEIGHT_MM = 297

case_no = 9999
p = Patient.objects.get(case_no=case_no)
print('Recomputing for patient', p.case_no)

prescriptions = list(Prescription.objects.filter(patient=p).order_by('created_at'))
prev_lower_abs = MARGIN_MM

for pres in prescriptions:
    height = pres.calculate_printed_height_mm()
    proposed_top_abs = prev_lower_abs + MARGIN_GAP_MM
    proposed_bottom_abs = proposed_top_abs + height
    if proposed_bottom_abs > A4_HEIGHT_MM:
        top_rel = MARGIN_GAP_MM
        prev_lower_abs = MARGIN_MM + top_rel + height
    else:
        top_rel = max(MARGIN_GAP_MM, proposed_top_abs - MARGIN_MM)
        prev_lower_abs = MARGIN_MM + top_rel + height
    pres.top_margin_mm = top_rel
    pres.printed_height_mm = height
    pres.save(update_fields=['top_margin_mm','printed_height_mm'])
    print(pres.case, '-> top_rel', top_rel, 'abs_top', top_rel+MARGIN_MM, 'bottom', prev_lower_abs)

p.page_lower_margin_mm = prev_lower_abs
p.save(update_fields=['page_lower_margin_mm'])
print('Patient page_lower_margin_mm set to', p.page_lower_margin_mm)
