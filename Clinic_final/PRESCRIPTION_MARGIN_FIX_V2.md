# Prescription Margin Fix - Version 2 (Improved Algorithm)

## Previous Issue
Prescriptions 3 and 4 were printing at the same position without allowing the user to choose between same page or new page.

## Root Cause
The previous implementation using modulo (`% A4_HEIGHT_MM`) caused prescriptions to wrap around and recalculate, leading to duplicate positions.

## Solution: Simple Position-Based Algorithm (No Modulo)

Instead of using complex modulo math, we now use straightforward comparisons:

```python
# When creating a prescription:
A4_HEIGHT_MM = 297
MARGIN_MM = 20
MARGIN_GAP_MM = 10

proposed_top_margin = patient.page_lower_margin_mm + MARGIN_GAP_MM
proposed_bottom = proposed_top_margin + prescription.printed_height_mm

if proposed_bottom > A4_HEIGHT_MM:
    # Doesn't fit - auto-move to new page
    prescription.top_margin_mm = MARGIN_MM + MARGIN_GAP_MM  # 30mm
    patient.page_lower_margin_mm = MARGIN_MM + MARGIN_GAP_MM + prescription.printed_height_mm
else:
    # Fits - place normally
    prescription.top_margin_mm = proposed_top_margin
    patient.page_lower_margin_mm = proposed_bottom
```

## How It Works

**Example with 5 prescriptions (heights: 100, 80, 100, 60, 70):**

| Prescription | Top Margin | Height | Bottom | Page | Fits Same Page? |
|---|---|---|---|---|---|
| 1st | 10mm | 100mm | 110mm | 1 | - (first) |
| 2nd | 120mm | 80mm | 200mm | 1 | ✓ Yes |
| 3rd | 30mm | 100mm | 130mm | 2 | ✗ No (auto-moved) |
| 4th | 140mm | 60mm | 200mm | 2 | ✓ Yes |
| 5th | 210mm | 70mm | 280mm | 2 | ✓ Yes |

## Modal Behavior

The "Same Page vs New Page" choice modal **only appears** when:
1. There are previous prescriptions AND
2. The current prescription actually fits on the page (`top_margin + height <= 297`)

This means:
- **1st prescription**: No modal (no previous)
- **2nd prescription**: ✓ Modal shown (fits on page 1, previous exists)
- **3rd prescription**: ✗ No modal (auto-moved, doesn't fit)
- **4th prescription**: ✓ Modal shown (fits on page 2, previous exists)
- **5th prescription**: ✓ Modal shown (fits on page 2, previous exists)

## Technical Details

- No complex modulo operations
- Clear, deterministic positioning
- Each prescription always has a valid `top_margin_mm` that represents its actual position
- `page_lower_margin_mm` tracks where the last prescription ended on the current page
- Prescriptions can span across multiple pages without overlapping

## Files Modified
- `Anand_Clinic/views.py` - Lines 1066-1090 (prescription creation)
- `Anand_Clinic/views.py` - Lines 1350-1398 (print view context)
