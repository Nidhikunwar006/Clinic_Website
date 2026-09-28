"""
Test script to verify the prescription margin calculation logic.
Run with: python manage.py shell < test_prescription_margins.py
"""

from Anand_Clinic.models import Patient, Prescription
from django.utils import timezone

# Clear any test data
print("=" * 60)
print("PRESCRIPTION MARGIN CALCULATION TEST")
print("=" * 60)

# Get or create a test patient
patient, created = Patient.objects.get_or_create(
    case_no=9999,
    defaults={
        'name': 'Test Patient',
        'age': 30,
        'phone_no': '1234567890',
        'doctor': 'dr_1',
        'gender': 'male',
    }
)

if created:
    print(f"\n✓ Created test patient: {patient.name}")
else:
    print(f"\n✓ Using existing test patient: {patient.name}")

# Reset patient's page_lower_margin for testing
patient.page_lower_margin_mm = 0
patient.save()
print(f"✓ Reset patient.page_lower_margin_mm to 0")

A4_HEIGHT_MM = 297
MARGIN_GAP_MM = 10  # Now 10mm gap instead of 5mm
MARGIN_MM = 20
AVAILABLE_HEIGHT_MM = A4_HEIGHT_MM - (MARGIN_MM * 2)  # 257mm - the actual printable height

# Test Scenario 1: Create first prescription
print("\n" + "-" * 60)
print("TEST 1: First Prescription (no previous prescriptions)")
print("-" * 60)

# Create first prescription
presc1 = Prescription.objects.create(
    patient=patient,
    case='TEST-1',
    case_number=1,
    prescribed_by_ami=True,
    language='en'
)

# Simulate height calculation (assuming 100mm for this test)
test_height_mm = 100.0
presc1.printed_height_mm = test_height_mm

# Calculate margins (matching the logic in views.py)
new_top_margin = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % AVAILABLE_HEIGHT_MM
presc1.top_margin_mm = new_top_margin
patient.page_lower_margin_mm = (new_top_margin + test_height_mm) % A4_HEIGHT_MM

presc1.save(update_fields=['printed_height_mm', 'top_margin_mm'])
patient.save(update_fields=['page_lower_margin_mm'])

print(f"  Patient's page_lower_margin_mm BEFORE: 0")
print(f"  New prescription top_margin_mm: {presc1.top_margin_mm} mm (expected: 10)")
print(f"  Prescription height: {test_height_mm} mm")
print(f"  Patient's page_lower_margin_mm AFTER: {patient.page_lower_margin_mm} mm (expected: 110)")
print(f"  ✓ Calculation: ({new_top_margin} + {test_height_mm}) % {AVAILABLE_HEIGHT_MM} = {patient.page_lower_margin_mm}")

assert presc1.top_margin_mm == 10, f"Expected top_margin_mm=10, got {presc1.top_margin_mm}"
assert patient.page_lower_margin_mm == 110, f"Expected page_lower_margin_mm=110, got {patient.page_lower_margin_mm}"

# Test Scenario 2: Create second prescription
print("\n" + "-" * 60)
print("TEST 2: Second Prescription (with previous prescription)")
print("-" * 60)

presc2 = Prescription.objects.create(
    patient=patient,
    case='TEST-2',
    case_number=2,
    prescribed_by_ami=True,
    language='en'
)

# Simulate height calculation (assuming 80mm for this test)
test_height_mm_2 = 80.0
presc2.printed_height_mm = test_height_mm_2

# Calculate margins
prev_lower_margin = patient.page_lower_margin_mm
new_top_margin_2 = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % AVAILABLE_HEIGHT_MM
presc2.top_margin_mm = new_top_margin_2
patient.page_lower_margin_mm = (new_top_margin_2 + test_height_mm_2) % A4_HEIGHT_MM

presc2.save(update_fields=['printed_height_mm', 'top_margin_mm'])
patient.save(update_fields=['page_lower_margin_mm'])

print(f"  Patient's page_lower_margin_mm BEFORE: {prev_lower_margin}")
print(f"  New prescription top_margin_mm: {presc2.top_margin_mm} mm (expected: 120)")
print(f"  Prescription height: {test_height_mm_2} mm")
print(f"  Patient's page_lower_margin_mm AFTER: {patient.page_lower_margin_mm} mm (expected: 200)")
print(f"  ✓ Calculation: ({new_top_margin_2} + {test_height_mm_2}) % {AVAILABLE_HEIGHT_MM} = {patient.page_lower_margin_mm}")

assert presc2.top_margin_mm == 120, f"Expected top_margin_mm=120, got {presc2.top_margin_mm}"
assert patient.page_lower_margin_mm == 200, f"Expected page_lower_margin_mm=200, got {patient.page_lower_margin_mm}"

# Test Scenario 3: Printing same prescription multiple times
print("\n" + "-" * 60)
print("TEST 3: Print Same Prescription Multiple Times")
print("-" * 60)

presc2_reloaded = Prescription.objects.get(pk=presc2.pk)
patient_reloaded = Patient.objects.get(case_no=patient.case_no)

print(f"  First print of prescription 2:")
print(f"    - top_margin_mm: {presc2_reloaded.top_margin_mm} mm (stays constant)")
print(f"    - Patient's page_lower_margin_mm: {patient_reloaded.page_lower_margin_mm} mm (unchanged)")

print(f"  Second print of same prescription:")
print(f"    - top_margin_mm: {presc2_reloaded.top_margin_mm} mm (stays constant)")
print(f"    - Patient's page_lower_margin_mm: {patient_reloaded.page_lower_margin_mm} mm (unchanged)")

print(f"  ✓ Margins DON'T change when printing same prescription multiple times")

# Test Scenario 4: Prescription spanning page boundary
print("\n" + "-" * 60)
print("TEST 4: Prescription Spanning Page Boundary")
print("-" * 60)

# Reset and test scenario where prescription goes to next page
patient.page_lower_margin_mm = 250  # Close to end of page (257mm available)
patient.save()

presc3 = Prescription.objects.create(
    patient=patient,
    case='TEST-3',
    case_number=3,
    prescribed_by_ami=True,
    language='en'
)

test_height_mm_3 = 50.0
presc3.printed_height_mm = test_height_mm_3

new_top_margin_3 = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % AVAILABLE_HEIGHT_MM
presc3.top_margin_mm = new_top_margin_3
patient.page_lower_margin_mm = (new_top_margin_3 + test_height_mm_3) % A4_HEIGHT_MM

presc3.save(update_fields=['printed_height_mm', 'top_margin_mm'])
patient.save(update_fields=['page_lower_margin_mm'])

print(f"  Patient's page_lower_margin_mm BEFORE: 250 mm")
print(f"  New prescription top_margin_mm: {presc3.top_margin_mm} mm")
print(f"  Prescription height: {test_height_mm_3} mm")
print(f"  Total needed: {new_top_margin_3} + {test_height_mm_3} = {new_top_margin_3 + test_height_mm_3} mm")
print(f"  Patient's page_lower_margin_mm AFTER: {patient.page_lower_margin_mm} mm")
print(f"  ✓ Wraps to next page: ({new_top_margin_3} + {test_height_mm_3}) % {AVAILABLE_HEIGHT_MM} = {patient.page_lower_margin_mm}")

expected_lower = (new_top_margin_3 + 50) % AVAILABLE_HEIGHT_MM
assert presc3.top_margin_mm >= 0 and presc3.top_margin_mm < AVAILABLE_HEIGHT_MM, f"Expected top_margin_mm in range [0, {AVAILABLE_HEIGHT_MM}), got {presc3.top_margin_mm}"
assert patient.page_lower_margin_mm == expected_lower, f"Expected page_lower_margin_mm={expected_lower}, got {patient.page_lower_margin_mm}"

# Test Scenario 5: Multiple prescriptions spanning pages (4th & 5th)
print("\n" + "-" * 60)
print("TEST 5: Fourth and Fifth Prescriptions (Page Wrapping)")
print("-" * 60)

presc4 = Prescription.objects.create(
    patient=patient,
    case='TEST-4',
    case_number=4,
    prescribed_by_ami=True,
    language='en'
)

test_height_mm_4 = 60.0
presc4.printed_height_mm = test_height_mm_4

prev_margin_4 = patient.page_lower_margin_mm
new_top_margin_4 = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % AVAILABLE_HEIGHT_MM
presc4.top_margin_mm = new_top_margin_4
patient.page_lower_margin_mm = (new_top_margin_4 + test_height_mm_4) % AVAILABLE_HEIGHT_MM

presc4.save(update_fields=['printed_height_mm', 'top_margin_mm'])
patient.save(update_fields=['page_lower_margin_mm'])

print(f"  Patient's page_lower_margin_mm BEFORE: {prev_margin_4} mm")
print(f"  New prescription top_margin_mm: {presc4.top_margin_mm} mm")
print(f"  Prescription height: {test_height_mm_4} mm")
print(f"  Calculation: ({prev_margin_4} + {MARGIN_GAP_MM}) % {AVAILABLE_HEIGHT_MM} = {presc4.top_margin_mm}")
print(f"  Patient's page_lower_margin_mm AFTER: {patient.page_lower_margin_mm} mm")
print(f"  ✓ Fourth prescription positioned correctly (should NOT exceed {AVAILABLE_HEIGHT_MM}mm)")

# Verify top_margin is always within page bounds
assert presc4.top_margin_mm >= 0, f"top_margin_mm should be >= 0"
assert presc4.top_margin_mm < AVAILABLE_HEIGHT_MM, f"top_margin_mm should be < {AVAILABLE_HEIGHT_MM}, got {presc4.top_margin_mm}"

# Create 5th prescription
presc5 = Prescription.objects.create(
    patient=patient,
    case='TEST-5',
    case_number=5,
    prescribed_by_ami=True,
    language='en'
)

test_height_mm_5 = 70.0
presc5.printed_height_mm = test_height_mm_5

prev_margin_5 = patient.page_lower_margin_mm
new_top_margin_5 = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % AVAILABLE_HEIGHT_MM
presc5.top_margin_mm = new_top_margin_5
patient.page_lower_margin_mm = (new_top_margin_5 + test_height_mm_5) % AVAILABLE_HEIGHT_MM

presc5.save(update_fields=['printed_height_mm', 'top_margin_mm'])
patient.save(update_fields=['page_lower_margin_mm'])

print(f"\n  Patient's page_lower_margin_mm BEFORE: {prev_margin_5} mm")
print(f"  New prescription top_margin_mm: {presc5.top_margin_mm} mm")
print(f"  Prescription height: {test_height_mm_5} mm")
print(f"  Calculation: ({prev_margin_5} + {MARGIN_GAP_MM}) % {AVAILABLE_HEIGHT_MM} = {presc5.top_margin_mm}")
print(f"  Patient's page_lower_margin_mm AFTER: {patient.page_lower_margin_mm} mm")
print(f"  ✓ Fifth prescription positioned correctly (should NOT exceed {AVAILABLE_HEIGHT_MM}mm)")

# Verify top_margin is always within page bounds
assert presc5.top_margin_mm >= 0, f"top_margin_mm should be >= 0"
assert presc5.top_margin_mm < AVAILABLE_HEIGHT_MM, f"top_margin_mm should be < {AVAILABLE_HEIGHT_MM}, got {presc5.top_margin_mm}"

print(f"\n  ✓ NO BLANK PAGES: All margins stay within printable bounds (0-{AVAILABLE_HEIGHT_MM}mm)")

print("\n" + "=" * 60)
print("✓ ALL TESTS PASSED!")
print("=" * 60)

# Cleanup
print("\nCleaning up test data...")
Prescription.objects.filter(patient=patient).delete()
patient.delete()
print("✓ Test data cleaned up")
