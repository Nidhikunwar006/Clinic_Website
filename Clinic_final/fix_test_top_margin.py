from Anand_Clinic.models import Prescription

p = Prescription.objects.filter(case='TEST-3').first()
if not p:
    print('No TEST-3 prescription found')
else:
    print('Before:', p.top_margin_mm)
    if p.top_margin_mm >= 20:
        p.top_margin_mm = p.top_margin_mm - 20
        p.save(update_fields=['top_margin_mm'])
        print('Updated top_margin_mm to', p.top_margin_mm)
    else:
        print('No update needed')
