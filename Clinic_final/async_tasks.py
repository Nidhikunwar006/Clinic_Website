from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import sqlite3
from datetime import datetime, timedelta
from whatsapp_msg_sender import send_whatsapp_template,send_whatsapp_text
import asyncio

# a function to fetch all follow-ups that have exactly 24 hours remaining in their appointment time from current time
# and reminder has not been sent yet, so create another function to take in those follow-ups and print their name with custom msg
# also that function should modify the reminder status..

# wrapper function...
def wrapper_for_fetching_followups_and_send_reminders():
    asyncio.run(fetch_followups_and_send_reminders())

async def fetch_followups_and_send_reminders():
    # Connect to SQLite database
    db = sqlite3.connect('db.sqlite3')
    cursor = db.cursor()

    # fetching all followups 
    query = """
            select id, scheduled_date, patient_id from Anand_Clinic_followup 
            where status='scheduled' 
            AND scheduled_date BETWEEN datetime('now') AND datetime('now', '+24 hours')
            and reminder_sent=0
            """
    followups = cursor.execute(query).fetchall()
    count = len(followups)
    print(f"\nRecursive Function\nFollowups: {count}\n")

    # for testing whatsapp reminders...
    tasks = []
    for followup in followups:
        p_id = followup[2]
        name,phone_no = cursor.execute("select name,phone_no from Anand_Clinic_patient where case_no = ?",(p_id,)).fetchone()

        # actual task to be performed with each of the followups to send them reminders
        test_reminder_task(name=name,custom_msg="Trying to send reminder")
        # send reminders asynchronously to each patient in followup..
        tasks.append( send_and_update(cursor,p_id,phone_no,"hello_world",[]) )
    
    # wait for all all reminders (tasks) to be completed...
    await asyncio.gather(*tasks)

    # commit or update the actual databse
    db.commit()
    db.close()

# async function to send whatsapp msg and update database
async def send_and_update(cursor: sqlite3.Cursor,patient_id: str,phone_no: str,template_name: str,parameters=[]):
    try:
        sent = await send_whatsapp_template(phone_number=phone_no,template_name=template_name,parameters=[])

        # if reminder is sent then update the database...
        if sent:
            upadte_query=f"""
                        UPDATE Anand_Clinic_followup
                        SET reminder_sent=1
                        WHERE patient_id= ?    
                        """
            cursor.execute(upadte_query,(patient_id,))
            print("Database Updated!!\n")
        print()
    except Exception as e:
        print(e)

# function to be called for each follow up reminder
def test_reminder_task(name,custom_msg)->bool:
    try:
        print(f"Patient Name: {name}: {custom_msg}")
        return True
    except:
        print("\nError while executing the reminder task!!\n")
        return False

# task that needs to run continously...
count=1
def run_this_task():
        global count  
        print(f'{count}: Its running recursively...')
        count=count+1


# Global scheduler instance (only created once)
scheduler = None
_shutdown_registered = False

def start_scheduler():
    global scheduler, _shutdown_registered
    
    # Prevent creating multiple scheduler instances
    if scheduler is not None and scheduler.running:
        return

    scheduler = BackgroundScheduler()
    
    # adding the task to be performed on set intervals
    scheduler.add_job(
        wrapper_for_fetching_followups_and_send_reminders,      # replace this function with the desired task function
        IntervalTrigger(seconds=30),
        id='My Task',
        replace_existing=True
    )

    # starting the scheduler
    scheduler.start()

    # Register shutdown only once
    if not _shutdown_registered:
        atexit.register(lambda: scheduler.shutdown())
        _shutdown_registered = True