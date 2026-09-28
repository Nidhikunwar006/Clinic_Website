from Anand_Clinic.models import Prescription

MARGIN_MM = 20
updated = []
for p in Prescription.objects.filter(case__startswith='TEST'):
    try:
        if p.top_margin_mm is None:
            continue
        if p.top_margin_mm >= MARGIN_MM:
            p.top_margin_mm = max(0, p.top_margin_mm - MARGIN_MM)
            p.save(update_fields=['top_margin_mm'])
            updated.append((p.case, p.top_margin_mm))
    except Exception as e:
        print('error for', p.case, e)

print('Updated entries:', updated)
