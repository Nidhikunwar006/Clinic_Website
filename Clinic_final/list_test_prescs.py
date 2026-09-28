from Anand_Clinic.models import Prescription
for p in Prescription.objects.filter(case__startswith='TEST').order_by('created_at'):
    print(p.id, p.case, p.top_margin_mm, p.printed_height_mm, p.created_at)
