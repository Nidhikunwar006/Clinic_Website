# WhatsApp Reminder Service - Setup & Integration Guide

## 📋 Overview

This guide explains how to set up the automatic WhatsApp reminder system for patient follow-ups. The system will automatically send reminders 24 hours before scheduled appointments.

### Key Features
- ✅ Automatic checks for follow-ups within 24 hours
- ✅ Only sends to patients who haven't received reminders yet
- ✅ Uses `reminder_sent` boolean flag in the FollowUp model
- ✅ Modular design for easy testing and maintenance
- ✅ Comprehensive error handling and logging
- ✅ Configurable batch sizes to prevent server overload
- ✅ Dry-run mode for testing without sending actual messages

---

## 🚀 Quick Start

### Step 1: Configure Environment Variables

Add these to your `.env` file (or set them in your hosting platform):

```bash
# WhatsApp Cloud API Credentials
WHATSAPP_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_API_VERSION=v21.0  # Optional, defaults to v21.0
```

**Where to get these credentials:**
1. Go to [Facebook Business Platform](https://business.facebook.com/)
2. Create a WhatsApp Business App
3. Follow WhatsApp's official documentation to get your access token and phone number ID

### Step 2: Verify the FollowUp Model

The `FollowUp` model already has the `reminder_sent` boolean field. No changes needed!

```python
# In Anand_Clinic/models.py
class FollowUp(models.Model):
    # ... other fields ...
    reminder_sent = models.BooleanField(default=False)  # ✅ Already exists!
```

### Step 3: Install Required Packages

```bash
pip install django-apscheduler
# or for production use with Celery:
pip install celery celery-beat
```

---

## 💻 Usage Methods

### Method 1: Manual Command Line (Testing)

Run reminders immediately from the command line:

```bash
# Actually send reminders
python manage.py send_reminders

# Test without sending (dry-run mode)
python manage.py send_reminders --dry-run

# Process different batch sizes
python manage.py send_reminders --batch=20
```

---

### Method 2: APScheduler (Recommended for Development)

APScheduler runs background tasks at intervals without needing external services.

#### Setup Instructions:

**1. Install APScheduler:**
```bash
pip install django-apscheduler
```

**2. Add to INSTALLED_APPS in `Clinic/settings.py`:**
```python
INSTALLED_APPS = [
    'Anand_Clinic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'widget_tweaks',
    'django_apscheduler',  # ✅ Add this line
]
```

**3. Create scheduler config in `Clinic/settings.py` (at the end):**
```python
# APScheduler Configuration
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"

SCHEDULER_CONFIG = {
    "apscheduler.jobstores.default": {
        "class": "apscheduler.jobstores.memory:MemoryJobStore"
    },
    "apscheduler.executors.default": {
        "class": "apscheduler.executors.pool:ThreadPoolExecutor",
        "max_workers": "10"
    },
    "apscheduler.job_defaults.coalesce": "false",
    "apscheduler.job_defaults.max_instances": "1",
    "apscheduler.timezone": "UTC",  # Or your timezone: "Asia/Kolkata"
}
```

**4. Create a signals file to auto-start the scheduler in `Anand_Clinic/scheduler.py`:**

```python
"""
Background scheduler for WhatsApp reminder service.
This module automatically starts when Django starts.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from reminder_service import run_reminder_scheduler

logger = logging.getLogger(__name__)


def start_scheduler():
    """
    Initialize and start the APScheduler background task runner.
    
    Configuration:
    - Interval: Every 15 minutes
    - Job: Check and send WhatsApp reminders
    - This runs continuously in a background thread
    """
    scheduler = BackgroundScheduler()
    
    # Add the reminder check job to run every 15 minutes
    # Adjust the minutes parameter to change frequency:
    # - 5 minutes: More frequent checks, more server load
    # - 15 minutes: Balanced (recommended)
    # - 30 minutes: Less frequent, lighter server load
    # - 60 minutes: Once per hour
    scheduler.add_job(
        run_reminder_scheduler,
        'interval',
        minutes=1,
        id='whatsapp_reminder_scheduler',
        name='WhatsApp Reminder Service',
        replace_existing=True,
        misfire_grace_time=60  # Allow up to 1 minute late execution
    )
    
    scheduler.start()
    logger.info("✅ WhatsApp Reminder Scheduler started (runs every 15 minutes)")


# Auto-start on Django startup (called from apps.py)
```

**5. Update `Anand_Clinic/apps.py` to auto-start the scheduler:**

```python
"""
Django app configuration for Anand Clinic.
Automatically starts the background reminder scheduler on startup.
"""

from django.apps import AppConfig


class AnandClinicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Anand_Clinic'
    verbose_name = 'Anand Clinic Management System'

    def ready(self):
        """
        Called when Django starts.
        This is where we initialize background tasks.
        """
        # Import here to avoid circular imports
        try:
            from .scheduler import start_scheduler
            start_scheduler()
        except Exception as e:
            print(f"⚠️ Failed to start reminder scheduler: {e}")
            # Don't crash Django startup if scheduler fails
```

**6. That's it!** Start Django normally:
```bash
python manage.py runserver
```

Now reminders will automatically check every 15 minutes!

---

### Method 3: Celery + Celery Beat (Recommended for Production)

Celery provides distributed task execution with better performance and reliability.

#### Setup Instructions:

**1. Install Celery:**
```bash
pip install celery celery-beat redis
```

**2. Create `Clinic/celery.py`:**
```python
"""
Celery configuration for distributed task execution.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Clinic.settings')

app = Celery('Clinic')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all Django apps
app.autodiscover_tasks()


# Configure Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'send-whatsapp-reminders': {
        'task': 'Anand_Clinic.tasks.send_reminders_task',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}

# Additional Celery configuration
app.conf.timezone = 'UTC'
```

**3. Update `Clinic/__init__.py`:**
```python
# This ensures Celery app is loaded on Django startup
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**4. Create `Anand_Clinic/tasks.py`:**
```python
"""
Celery tasks for background job execution.
"""

from celery import shared_task
from reminder_service import run_reminder_scheduler
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_reminders_task():
    """
    Celery task to execute reminder checking and sending.
    Scheduled to run every 15 minutes via Celery Beat.
    """
    logger.info("🕐 Celery task: Starting reminder check...")
    stats = run_reminder_scheduler()
    logger.info(f"✅ Celery task completed: {stats['reminders_sent']} reminders sent")
    return stats
```

**5. Add Celery config to `Clinic/settings.py`:**
```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

**6. Start Celery Workers:**

Terminal 1 - Start Worker:
```bash
celery -A Clinic worker --loglevel=info
```

Terminal 2 - Start Beat Scheduler:
```bash
celery -A Clinic beat --loglevel=info
```

---

## 🧪 Testing the System

### Test Without Sending Messages (Dry Run)

```bash
# See what reminders would be sent
python manage.py send_reminders --dry-run
```

Check the console output for messages that would be sent.

### Test Sending Actual Messages

```bash
# Actually send reminders to patients
python manage.py send_reminders
```

Monitor Django logs to see success/failure messages.

### Direct Python Testing

```python
# In Django shell: python manage.py shell

from reminder_service import check_and_send_followup_reminders, send_whatsapp_reminder

# Test 1: Dry run check
stats = check_and_send_followup_reminders(batch_size=10, dry_run=True)
print(f"Would send {stats['reminders_sent']} reminders")

# Test 2: Send a test message to yourself
result = send_whatsapp_reminder("91XXXXXXXXXX", "Hello! This is a test message.")
print(f"Success: {result['success']}, Message ID: {result['message_id']}")

# Test 3: Actually send reminders
stats = check_and_send_followup_reminders(batch_size=10, dry_run=False)
print(f"Sent {stats['reminders_sent']} reminders")
```

---

## 📊 Monitoring & Logging

### View Logs

The reminder service logs to Django's logging system. Configure in `Clinic/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/reminder_service.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'reminder_service': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Check Reminder Status in Admin

```python
# In Anand_Clinic/admin.py, add this to display reminder status
@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['patient', 'scheduled_date', 'status', 'reminder_sent']
    list_filter = ['status', 'reminder_sent', 'scheduled_date']
    search_fields = ['patient__name']
```

---

## ⚙️ Configuration & Tuning

### Batch Size

Controls how many reminders to process per run. Adjust based on your server capacity:

```bash
# Light load: Check 5 reminders
python manage.py send_reminders --batch=5

# Default: Check 10 reminders
python manage.py send_reminders --batch=10

# Heavy load: Check 50 reminders
python manage.py send_reminders --batch=50
```

### Check Frequency

Adjust how often the system checks for reminders:

**APScheduler** - Edit in `Anand_Clinic/scheduler.py`:
```python
scheduler.add_job(
    run_reminder_scheduler,
    'interval',
    minutes=15,  # Change: 5, 15, 30, 60
    # ...
)
```

**Celery Beat** - Edit in `Clinic/celery.py`:
```python
'send-whatsapp-reminders': {
    'task': 'Anand_Clinic.tasks.send_reminders_task',
    'schedule': crontab(minute='*/15'),  # Change minute value
},
```

---

## 🔒 Security Considerations

1. **Store credentials in `.env` file, NEVER in code:**
   ```bash
   # .env file (add to .gitignore)
   WHATSAPP_TOKEN=secret_token_here
   WHATSAPP_PHONE_NUMBER_ID=phone_id_here
   ```

2. **Use environment variables in production:**
   - Heroku: Use Config Vars
   - AWS: Use Secrets Manager
   - Azure: Use Key Vault

3. **Monitor WhatsApp API logs** for rate limiting or failed messages

4. **Validate phone numbers** before storing in database

---

## ❌ Troubleshooting

### Reminders Not Sending

**Check 1: Are credentials configured?**
```bash
# In Django shell
import os
print(os.getenv("WHATSAPP_TOKEN"))  # Should show your token, not None
```

**Check 2: Are there follow-ups within 24 hours?**
```python
# In Django shell
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
print(f"Found {upcoming.count()} reminders to send")
```

**Check 3: Are patient phone numbers valid?**
```python
for patient in followup.patient_set.all():
    print(f"{patient.name}: {patient.phone_no}")
```

### Scheduler Not Running

**APScheduler:**
```python
# Check if scheduler started
from django.core.management import call_command
call_command('help send_reminders')
```

**Celery:**
```bash
# Check if workers are running
celery -A Clinic inspect active
```

---

## 📞 Support

For issues with:
- **WhatsApp API:** Check [Meta WhatsApp Business docs](https://developers.facebook.com/docs/whatsapp)
- **Django:** Refer to [Django documentation](https://docs.djangoproject.com/)
- **APScheduler:** See [APScheduler docs](https://apscheduler.readthedocs.io/)
- **Celery:** See [Celery docs](https://docs.celeryproject.io/)

---

## 🎯 Summary

| Method | Setup Time | Complexity | Best For | Load |
|--------|-----------|-----------|----------|------|
| Manual | Instant | 1/5 | Testing | None |
| APScheduler | 10 min | 2/5 | Small/Medium | Light |
| Celery | 30 min | 4/5 | Production | Heavy |

**Recommended:** Start with APScheduler for development, migrate to Celery for production.

Happy reminding! 🎉
