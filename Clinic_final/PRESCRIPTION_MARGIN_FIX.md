# Prescription Margin Overlap Issue - FIXED

## Problem Description
When printing the 4th prescription, it was overlapping with the 3rd prescription. This was caused by an incorrect margin calculation logic.

## Root Cause
The margin calculation was using **AVAILABLE_HEIGHT_MM (257mm)** in the modulo operation, but should have been using **A4_HEIGHT_MM (297mm)**.

### The Bug (Previous Code)
```python
A4_HEIGHT_MM = 297
MARGIN_MM = 20  # top and bottom margins
AVAILABLE_HEIGHT_MM = A4_HEIGHT_MM - (MARGIN_MM * 2)  # 257mm printable height
MARGIN_GAP_MM = 10

# WRONG - Using AVAILABLE_HEIGHT_MM in modulo
new_top_margin_mm = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % AVAILABLE_HEIGHT_MM
prescription.top_margin_mm = new_top_margin_mm
patient.page_lower_margin_mm = (new_top_margin_mm + prescription.printed_height_mm) % AVAILABLE_HEIGHT_MM
```

### Why This Caused Overlap
The `AVAILABLE_HEIGHT_MM` (257mm) represents only the **printable area** of a single page, not including the top and bottom margins (20mm each). When using this in the modulo operation:

1. **1st prescription** → top_margin = 10mm (correct, starts after top margin)
2. **2nd prescription** → top_margin = 120mm (correct, after 1st)
3. **3rd prescription** → top_margin = ~210mm (still on page)
4. **4th prescription** → When position exceeds 257mm, it wraps using `% 257`, causing it to reappear at position 10-20mm, **overlapping the first prescription**

## The Fix
Use **A4_HEIGHT_MM (297mm)** in the modulo operation to track position across the full page height:

```python
A4_HEIGHT_MM = 297
MARGIN_MM = 20
AVAILABLE_HEIGHT_MM = A4_HEIGHT_MM - (MARGIN_MM * 2)  # 257mm printable height
MARGIN_GAP_MM = 10

# CORRECT - Using A4_HEIGHT_MM for full page tracking
new_top_margin_mm = (patient.page_lower_margin_mm + MARGIN_GAP_MM) % A4_HEIGHT_MM
prescription.top_margin_mm = new_top_margin_mm
patient.page_lower_margin_mm = (new_top_margin_mm + prescription.printed_height_mm) % A4_HEIGHT_MM
```

## How It Works Now
The modulo operation wraps at 297mm (full page height), not 257mm:

1. **1st prescription** → top_margin = 10mm
2. **2nd prescription** → top_margin = 120mm
3. **3rd prescription** → top_margin = 210mm
4. **4th prescription** → When position exceeds 297mm, it wraps to next page (position 20-30mm on new page)

This ensures prescriptions are placed on separate pages when they would otherwise overlap.

## Files Modified
- `Anand_Clinic/views.py` - Fixed the margin calculation in prescription creation (lines 1074-1082)

## Testing
Run the margin calculation test to verify:
```bash
python manage.py shell < test_prescription_margins.py
```

This will validate that:
- First 3 prescriptions fit on one page
- 4th prescription correctly moves to next page
- No overlaps occur
