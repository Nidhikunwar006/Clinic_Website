import sqlite3
import os

def remove_sample_data():
    """
    Removes all patient API data, medicine data, followups, prescriptions, etc.
    Does NOT remove users, profiles, or authentication details.
    """
    db_path = os.path.join(os.getcwd(), 'db.sqlite3')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tables to clear related to patients, prescriptions, medicines, notes, and followups
    tables_to_clear = [
        'Anand_Clinic_personalnoteimage',
        'Anand_Clinic_personalnote',
        'Anand_Clinic_firstdayinstruction',
        'Anand_Clinic_nextdayinstruction',
        'Anand_Clinic_prescription',
        'Anand_Clinic_visit',
        'Anand_Clinic_followup',
        'Anand_Clinic_checkin',
        'Anand_Clinic_stocktransaction',
        'Anand_Clinic_medicine',
        'Anand_Clinic_patient',
    ]

    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table};")
            # Reset the sqlite_sequence (auto-increment counter) for the table
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
            print(f"Cleared data and reset sequence for table: {table}")
        except sqlite3.Error as e:
            print(f"Error clearing {table}: {e}")

    conn.commit()
    conn.close()
    print("Successfully removed all patient and medicine related sample data.")

if __name__ == '__main__':
    remove_sample_data()
