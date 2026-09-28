import os
import sqlite3

# Resolve database path from settings.py BASE_DIR (project root)
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at: {DB_PATH}")
        return 1

    con = sqlite3.connect(DB_PATH)
    try:
        # Temporarily disable FK checks to allow corrective updates/deletes
        con.execute('PRAGMA foreign_keys = OFF;')
        # 1) Relink prescriptions to the correct patient using case_number where available
        con.executescript("""
        UPDATE Anand_Clinic_prescription
        SET patient_id = case_number
        WHERE patient_id NOT IN (SELECT case_no FROM Anand_Clinic_patient)
          AND case_number IN (SELECT case_no FROM Anand_Clinic_patient);

        -- 2) Delete any remaining orphan prescriptions
        DELETE FROM Anand_Clinic_prescription
        WHERE patient_id NOT IN (SELECT case_no FROM Anand_Clinic_patient);

        -- 3) Remove orphan first day instructions
        DELETE FROM Anand_Clinic_firstdayinstruction
        WHERE prescription_id NOT IN (SELECT id FROM Anand_Clinic_prescription);

        -- 4) Remove orphan next day instructions
        DELETE FROM Anand_Clinic_nextdayinstruction
        WHERE prescription_id NOT IN (SELECT id FROM Anand_Clinic_prescription);

        -- 5) Remove orphan visits referencing missing patients
        DELETE FROM Anand_Clinic_visit
        WHERE patient_id NOT IN (SELECT case_no FROM Anand_Clinic_patient);

        -- 6) Remove orphan follow-ups referencing missing patients
        DELETE FROM Anand_Clinic_followup
        WHERE patient_id NOT IN (SELECT case_no FROM Anand_Clinic_patient);

        -- 7) Remove orphan check-ins referencing missing follow-ups
        DELETE FROM Anand_Clinic_checkin
        WHERE followup_id NOT IN (SELECT id FROM Anand_Clinic_followup);

        """)
        con.commit()
        # Conditionally clean StockTransaction if related_prescription exists
        try:
            cur = con.cursor()
            cols = [r[1] for r in cur.execute("PRAGMA table_info(Anand_Clinic_stocktransaction)").fetchall()]
            if 'related_prescription' in cols:
                cur.execute("""
                    DELETE FROM Anand_Clinic_stocktransaction
                    WHERE related_prescription IS NOT NULL
                      AND related_prescription NOT IN (SELECT id FROM Anand_Clinic_prescription);
                """)
                con.commit()
        except Exception:
            pass
        # Re-enable FK checks
        con.execute('PRAGMA foreign_keys = ON;')
        print("Orphan prescription cleanup completed successfully.")
        return 0
    except Exception as e:
        print(f"Cleanup failed: {e}")
        return 2
    finally:
        con.close()

if __name__ == "__main__":
    raise SystemExit(main())
