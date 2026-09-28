"""
Test script to verify the improved prescription margin calculation logic.
Run with: python manage.py shell < test_prescription_margins_v2.py
"""

from Anand_Clinic.models import Patient, Prescription
from django.utils import timezone

# Clear test data
print("=" * 70)
print("PRESCRIPTION MARGIN CALCULATION TEST - VERSION 2 (No Modulo)")
print("=" * 70)

# Get or create a test patient
patient, created = Patient.objects.get_or_create(
    case_no=9999,
    defaults={
        'name': 'Test Patient V2',
        'age': 30,
        'phone_no': '1234567890',
        'doctor': 'dr_1',
        'gender': 'male',
    }
)

# Reset for clean test
patient.page_lower_margin_mm = 0
patient.save()

print(f"\n✓ Starting with patient.page_lower_margin_mm = 0")

A4_HEIGHT_MM = 297
MARGIN_MM = 20
MARGIN_GAP_MM = 10

prescriptions = []
prescriptions_data = [
    {'height': 100, 'name': '1st'},
    {'height': 80, 'name': '2nd'},
    {'height': 100, 'name': '3rd'},
    {'height': 60, 'name': '4th'},
    {'height': 70, 'name': '5th'},
]

for presc_data in prescriptions_data:
    print("\n" + "-" * 70)
    print(f"{presc_data['name'].upper()} PRESCRIPTION")
    print("-" * 70)
    
    presc = Prescription.objects.create(
        patient=patient,
        case=f'TEST-{len(prescriptions)+1}',
        case_number=len(prescriptions)+1,
        prescribed_by_ami=True,
        language='en'
    )
    
    height = float(presc_data['height'])
    presc.printed_height_mm = height
    
    # Calculate position using the new scheme (store top_margin relative to printable area)
    proposed_top_abs = patient.page_lower_margin_mm + MARGIN_GAP_MM
    proposed_bottom_abs = proposed_top_abs + height

    prev_lower = patient.page_lower_margin_mm

    print(f"  Previous page_lower_margin: {prev_lower} mm")
    print(f"  Proposed top_margin (abs): {proposed_top_abs} mm")
    print(f"  Proposed bottom (abs): {proposed_bottom_abs} mm")
    print(f"  Page height: {A4_HEIGHT_MM} mm")

    if proposed_bottom_abs > A4_HEIGHT_MM:
        print(f"  ⚠️  EXCEEDS PAGE → Moving to new page")
        # Store relative top margin (gap only)
        presc.top_margin_mm = MARGIN_GAP_MM
        # Update absolute lower margin on patient
        patient.page_lower_margin_mm = MARGIN_MM + presc.top_margin_mm + height
        fits_on_same = False
    else:
        print(f"  ✓ Fits on same page")
        # Store top margin relative to printable area and clamp to gap
        presc.top_margin_mm = max(MARGIN_GAP_MM, proposed_top_abs - MARGIN_MM)
        # Update absolute lower margin on patient
        patient.page_lower_margin_mm = MARGIN_MM + presc.top_margin_mm + height
        fits_on_same = True
    
    presc.save(update_fields=['printed_height_mm', 'top_margin_mm'])
    patient.save(update_fields=['page_lower_margin_mm'])
    
    print(f"  New top_margin: {presc.top_margin_mm} mm")
    print(f"  New page_lower_margin: {patient.page_lower_margin_mm} mm")
    print(f"  Space check: {presc.top_margin_mm} + {height} = {presc.top_margin_mm + height} mm {'✓' if presc.top_margin_mm + height <= A4_HEIGHT_MM else '✗'}")
    
    prescriptions.append({
        'obj': presc,
        'height': height,
        'fits_on_same': fits_on_same
    })

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

for i, p in enumerate(prescriptions, 1):
    print(f"\nPrescription {i}:")
    print(f"  top_margin: {p['obj'].top_margin_mm} mm")
    print(f"  height: {p['height']} mm")
    print(f"  bottom: {p['obj'].top_margin_mm + p['height']} mm")
    print(f"  fits check: {p['obj'].top_margin_mm + p['height']} <= {A4_HEIGHT_MM} = {p['obj'].top_margin_mm + p['height'] <= A4_HEIGHT_MM}")
    print(f"  fits_on_same_page_as_prev: {p['fits_on_same']}")

print("\n✓ Test complete!")
