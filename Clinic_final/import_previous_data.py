"""
Import Previous Patient Data Script
This script reads patient data from an Excel file in Anand_Clinic/Previous data/
and imports it into the Patient database.

Usage:
    python import_previous_data.py

The Excel file should contain columns:
    - NAME: Patient name
    - AGE / SEX: Format like "47 / M" or "16 / F"
    - ADDRESS: Patient address
    - CONTACT NO. 1: Primary phone number
    - Case No.: Case number (optional)
    - Date: Appointment date (optional)
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Clinic.settings')
django.setup()

from Anand_Clinic.models import Patient

# Configuration
EXCEL_FILE_PATH = 'Anand_Clinic/Previous data/trial.xlsx'
DEFAULT_DOCTOR = 'dr_1'  # Default to first doctor


def parse_age_sex(age_sex_str):
    """
    Parse the AGE / SEX column value into separate age and gender.
    
    Args:
        age_sex_str: String in format "47 / M" or "16 / F"
    
    Returns:
        tuple: (age_int, gender_str) where gender is 'male', 'female', or 'other'
    """
    if pd.isna(age_sex_str):
        return None, None
    
    try:
        # Split by " / "
        parts = str(age_sex_str).split('/')
        if len(parts) != 2:
            print(f"Warning: Invalid AGE / SEX format: {age_sex_str}")
            return None, None
        
        age = int(parts[0].strip())
        sex = parts[1].strip().upper()
        
        # Map sex codes to database choices
        if sex in ['M', 'MALE']:
            gender = 'male'
        elif sex in ['F', 'FEMALE']:
            gender = 'female'
        else:
            gender = 'other'
        
        return age, gender
    
    except (ValueError, AttributeError) as e:
        print(f"Warning: Error parsing AGE / SEX '{age_sex_str}': {e}")
        return None, None


def clean_phone_number(phone_str):
    """
    Clean phone number to ensure it's valid (10 digits for India).
    
    Args:
        phone_str: Phone number (can be int or str)
    
    Returns:
        str: Cleaned 10-digit phone number or None if invalid
    """
    if pd.isna(phone_str):
        return None
    
    try:
        # Convert to string and remove non-digit characters
        phone = str(int(float(phone_str)))
        
        # Take last 10 digits if longer
        if len(phone) >= 10:
            phone = phone[-10:]
        elif len(phone) < 10:
            print(f"Warning: Phone number too short: {phone_str}")
            return None
        
        return phone
    
    except (ValueError, TypeError) as e:
        print(f"Warning: Invalid phone number: {phone_str}")
        return None


def parse_appointment_date(date_val):
    """
    Parse appointment date from Excel.
    
    Args:
        date_val: Date value from Excel
    
    Returns:
        datetime: Parsed datetime or None if invalid
    """
    if pd.isna(date_val):
        return None
    
    try:
        if isinstance(date_val, str):
            return datetime.strptime(date_val, '%Y-%m-%d')
        else:
            # Pandas automatically converts dates
            return pd.Timestamp(date_val).to_pydatetime()
    
    except (ValueError, TypeError) as e:
        print(f"Warning: Invalid date: {date_val}")
        return None


def import_data():
    """Main function to import patient data from Excel."""
    
    # Check if file exists
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"Error: File not found at {EXCEL_FILE_PATH}")
        sys.exit(1)
    
    # Read Excel file
    print(f"Reading Excel file: {EXCEL_FILE_PATH}")
    df = pd.read_excel(EXCEL_FILE_PATH)
    
    print(f"Found {len(df)} rows to import")
    
    imported_count = 0
    skipped_count = 0
    duplicate_count = 0
    
    # Process each row
    for idx, row in df.iterrows():
        try:
            # Extract and validate required fields
            # NAME may sometimes be non-string types; coerce safely
            raw_name = row.get('NAME', '')
            if pd.isna(raw_name):
                name = ''
            else:
                name = str(raw_name).strip()

            # In this Excel file the primary phone is in 'CONTACT NO. 2'
            # and 'CONTACT NO. 1' actually contains the address text.
            phone_no = clean_phone_number(row.get('CONTACT NO. 2'))

            raw_address = row.get('CONTACT NO. 1') or row.get('ADDRESS')
            if pd.isna(raw_address):
                address = ''
            else:
                address = str(raw_address).strip()

            case_no = row.get('Case No.', '')
            
            # Parse age and sex
            age, gender = parse_age_sex(row.get('AGE / SEX'))
            
            # Parse appointment date
            appointment_date = parse_appointment_date(row.get('Date'))
            
            # Validate required fields
            if not name:
                print(f"Row {idx + 1}: Skipped - Missing patient name")
                skipped_count += 1
                continue
            
            if not phone_no:
                print(f"Row {idx + 1}: Skipped - Invalid phone number")
                skipped_count += 1
                continue
            
            if age is None or gender is None:
                print(f"Row {idx + 1}: Skipped - Invalid AGE / SEX format")
                skipped_count += 1
                continue
            
            # Check if patient already exists (by name and phone)
            if Patient.objects.filter(name=name, phone_no=phone_no).exists():
                print(f"Row {idx + 1}: Skipped - Patient already exists ({name}, {phone_no})")
                duplicate_count += 1
                continue
            
            # Create patient record
            patient = Patient(
                name=name,
                age=age,
                phone_no=phone_no,
                gender=gender,
                doctor=DEFAULT_DOCTOR,
                address=address if address else None,
                case=str(case_no) if case_no and pd.notna(case_no) else None,
                appointment_date=appointment_date if appointment_date else django.utils.timezone.now()
            )
            
            patient.save()
            imported_count += 1
            print(f"Row {idx + 1}: ✓ Imported - {name} ({age}/{gender[0].upper()})")
        
        except Exception as e:
            print(f"Row {idx + 1}: Error - {str(e)}")
            skipped_count += 1
    
    # Print summary
    print("\n" + "="*60)
    print("IMPORT SUMMARY")
    print("="*60)
    print(f"Total rows processed:    {len(df)}")
    print(f"Successfully imported:   {imported_count}")
    print(f"Duplicates skipped:      {duplicate_count}")
    print(f"Errors/Skipped:          {skipped_count}")
    print("="*60)


if __name__ == '__main__':
    import_data()
