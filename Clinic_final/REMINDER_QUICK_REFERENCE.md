# 🚀 WhatsApp Reminder Service - Quick Reference Guide

## 📁 Files Created

```
Your_Project/
├── reminder_service.py                          # 🎯 MAIN SERVICE FILE
│   ├── send_whatsapp_reminder()                # Send single reminder
│   ├── check_and_send_followup_reminders()    # Check & send batch
│   └── run_reminder_scheduler()                # Background task runner
│
├── Anand_Clinic/
│   ├── scheduler.py                             # APScheduler configuration
│   │   ├── start_scheduler()                   # Start background checks
│   │   ├── stop_scheduler()                    # Stop background checks
│   │   └── get_scheduler_status()              # Get scheduler info
│   │
│   ├── apps.py                                  # ✅ UPDATED for auto-start
│   │
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── send_reminders.py               # CLI command
│   │
│   └── tests_reminder_service.py               # Full test suite
│
└── REMINDER_SERVICE_SETUP.md                   # Detailed setup guide
```

---

## 🎯 Function Overview

### Core Functions

#### 1. **send_whatsapp_reminder()** - LOW-LEVEL
**Purpose:** Send a single WhatsApp message

```python
from reminder_service import send_whatsapp_reminder

result = send_whatsapp_reminder(
    patient_phone_number="919876543210",
    reminder_message="Your appointment is tomorrow at 10 AM"
)

if result['success']:
    print(f"✅ Sent! Message ID: {result['message_id']}")
else:
    print(f"❌ Failed: {result['error']}")
```

**Parameters:**
- `patient_phone_number` (str): Phone in format "91XXXXXXXXXX"
- `reminder_message` (str): Message text to send

**Returns:**
```python
{
    'success': bool,        # Was message sent?
    'status_code': int,     # HTTP status code
    'message_id': str,      # WhatsApp message ID
    'error': str,           # Error message if failed
    'response': dict        # Full API response
}
```

---

#### 2. **check_and_send_followup_reminders()** - HIGH-LEVEL
**Purpose:** Find patients needing reminders and send them

```python
from reminder_service import check_and_send_followup_reminders

# Actually send reminders
stats = check_and_send_followup_reminders(batch_size=10, dry_run=False)

# Or test without sending
stats = check_and_send_followup_reminders(batch_size=10, dry_run=True)

print(f"Sent: {stats['reminders_sent']}")
print(f"Failed: {stats['reminders_failed']}")
print(f"Errors: {stats['errors']}")
```

**Parameters:**
- `batch_size` (int): Max reminders per run (default: 10)
- `dry_run` (bool): Test mode? (default: False)

**Returns:**
```python
{
    'total_processed': int,      # How many checked
    'reminders_sent': int,       # Successfully sent
    'reminders_failed': int,     # Failed
    'reminders_skipped': int,    # Already sent
    'dry_run': bool,             # Was this a test?
    'errors': list               # Error messages
}
```

---

#### 3. **run_reminder_scheduler()** - BACKGROUND TASK
**Purpose:** Check for reminders every 15 minutes (automatic)

```python
# This is called automatically by the scheduler every 15 minutes
# You don't need to call this directly!

# But you can call it manually:
from reminder_service import run_reminder_scheduler

stats = run_reminder_scheduler()
```

---

### Scheduler Functions

#### 4. **start_scheduler()**
**Purpose:** Start the background reminder checker

```python
from Anand_Clinic.scheduler import start_scheduler

start_scheduler()
# Now runs every 15 minutes automatically!
```

#### 5. **get_scheduler_status()**
**Purpose:** Check if scheduler is running

```python
from Anand_Clinic.scheduler import get_scheduler_status

status = get_scheduler_status()
print(f"Running: {status['running']}")
print(f"Jobs: {status['job_count']}")
for job in status['jobs']:
    print(f"  - {job['name']} (next: {job['next_run_time']})")
```

---

## 🔧 Quick Start

### 1. Install Dependencies
```bash
pip install django-apscheduler requests python-dotenv
```

### 2. Add .env File
```bash
# .env (in project root)
WHATSAPP_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id_here
```

### 3. Test Manually
```bash
# Django shell
python manage.py shell

# Test sending a message
from reminder_service import send_whatsapp_reminder
result = send_whatsapp_reminder("919876543210", "Hello!")
print(result)

# Test checking for reminders
from reminder_service import check_and_send_followup_reminders
stats = check_and_send_followup_reminders(dry_run=True)
print(f"Would send: {stats['reminders_sent']}")
```

### 4. Start Automatic Reminders
```bash
# Start Django (scheduler auto-starts)
python manage.py runserver

# In another terminal, test manually
python manage.py send_reminders --dry-run
python manage.py send_reminders
```

---

## 📝 Common Commands

### Run via Management Command

```bash
# Actually send reminders
python manage.py send_reminders

# Test without sending
python manage.py send_reminders --dry-run

# Process 20 reminders
python manage.py send_reminders --batch=20

# Combine options
python manage.py send_reminders --batch=20 --dry-run
```

### Run via Django Shell

```bash
python manage.py shell

# Test single message
from reminder_service import send_whatsapp_reminder
result = send_whatsapp_reminder("919876543210", "Test")
print(result['success'])

# Test finding reminders
from reminder_service import check_and_send_followup_reminders
stats = check_and_send_followup_reminders(batch_size=5, dry_run=True)
print(stats)

# Check scheduler status
from Anand_Clinic.scheduler import get_scheduler_status
status = get_scheduler_status()
print(f"Scheduler running: {status['running']}")

# Exit
exit()
```

---

## 🐛 Troubleshooting

### Reminders Not Sending?

**Check 1: Credentials configured?**
```bash
python manage.py shell
import os
print("Token:", os.getenv("WHATSAPP_TOKEN"))
print("Phone ID:", os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
```

**Check 2: Follow-ups exist?**
```bash
python manage.py shell
from Anand_Clinic.models import FollowUp
from django.utils import timezone
from datetime import timedelta

now = timezone.now()
upcoming = FollowUp.objects.filter(
    status='scheduled',
    scheduled_date__gte=now,
    scheduled_date__lte=now + timedelta(hours=24),
    reminder_sent=False
)
print(f"Follow-ups needing reminders: {upcoming.count()}")
```

**Check 3: Run manually**
```bash
python manage.py send_reminders --dry-run
# Check console output for what would be sent
```

### Scheduler Not Running?

```bash
python manage.py shell
from Anand_Clinic.scheduler import get_scheduler_status
status = get_scheduler_status()
print(f"Scheduler running: {status['running']}")
print(f"Jobs: {status['jobs']}")
```

---

## 📊 Database Fields

The FollowUp model uses this field to track reminders:

```python
class FollowUp(models.Model):
    # ... other fields ...
    reminder_sent = models.BooleanField(default=False)  # ← This field!
    # ... other fields ...
```

**When to check:**
- `reminder_sent=False`: Reminder not sent yet
- `reminder_sent=True`: Reminder has been sent

---

## 🔐 Security Checklist

- ✅ Store credentials in `.env` file
- ✅ Add `.env` to `.gitignore`
- ✅ Never log full credentials
- ✅ Use environment variables in production
- ✅ Validate phone numbers before sending

---

## 📞 Support

For detailed setup instructions, see: **REMINDER_SERVICE_SETUP.md**

For code details, see: **reminder_service.py** (fully commented)

---

## 🎯 Key Design Decisions

| Decision | Reason |
|----------|--------|
| Two-function design | Modularity + testability |
| Boolean flag `reminder_sent` | Track what's been sent |
| 24-hour window | Optimal reminder timing |
| Batch processing | Server load management |
| Dry-run mode | Safe testing capability |
| APScheduler | No external dependencies |
| Management command | CLI flexibility |
| Comprehensive logging | Debugging & auditing |

---

Happy reminding! 🎉
