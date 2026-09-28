"""
Background scheduler for WhatsApp reminder service.

This module configures and starts the APScheduler background task runner
to automatically check for and send WhatsApp reminders every 15 minutes.

The scheduler is automatically initialized when Django starts (see apps.py).
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from reminder_service import run_reminder_scheduler

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

# Interval for checking reminders (in minutes)
# Change this to adjust how often the scheduler checks for reminders
interval = 5  # 🔧 ADJUST THIS: 5, 15, 30, or 60 minutes

def start_scheduler():
    """
    Initialize and start the APScheduler background task runner.
    
    Configuration Details:
    - Scheduler Type: BackgroundScheduler (runs in a background thread)
    - Interval: Every 15 minutes
    - Job: Check and send WhatsApp reminders
    - This runs continuously while Django is running
    
    Job Configuration:
    - run_reminder_scheduler: The function that checks for and sends reminders
    - 'interval' with 'minutes=15': Runs every 15 minutes
    - replace_existing=True: If scheduler restarts, replace old job with new one
    - misfire_grace_time=60: Allow up to 60 seconds late execution if the server is busy
    
    How to Adjust Frequency:
    - 5 minutes: More frequent checks, higher server load, faster reminders
    - 15 minutes: Balanced (default - RECOMMENDED)
    - 30 minutes: Less frequent, lighter load, slight delay in reminders
    - 60 minutes: Minimal load, but reminders may be delayed
    
    Example to change frequency:
        scheduler.add_job(
            run_reminder_scheduler,
            'interval',
            minutes=30,  # Change from 15 to 30
            ...
        )
    """
    global scheduler
    
    # Only start if not already running
    if scheduler is not None and scheduler.running:
        logger.info("⚠️  Scheduler already running, skipping restart")
        return
    
    try:
        # Create a background scheduler instance
        scheduler = BackgroundScheduler()
        
        # Configure the scheduler to use multithreading
        scheduler.configure(
            jobstores={
                'default': {
                    'class': 'apscheduler.jobstores.memory:MemoryJobStore'
                }
            },
            executors={
                'default': {
                    'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
                    'max_workers': '2'  # Use 2 background threads
                }
            },
            job_defaults={
                'coalesce': False,  # Don't combine missed jobs
                'max_instances': 1,  # Only 1 reminder check at a time
                'misfire_grace_time': 60  # Allow 60 seconds grace period
            },
            timezone='UTC'
        )
        
        # Add the reminder check job
        # This job will run every 15 minutes
        scheduler.add_job(
            run_reminder_scheduler,
            'interval',
            minutes=interval,  # 🔧 ADJUST THIS TO CHANGE CHECK FREQUENCY
            id='whatsapp_reminder_scheduler',  # Unique ID for this job
            name='WhatsApp Reminder Service',  # Human-readable name
            replace_existing=True,  # Replace if already exists
            misfire_grace_time=60  # Allow up to 1 minute late execution
        )
        
        # Start the scheduler
        scheduler.start()
        
        logger.info(
            "✅ WhatsApp Reminder Scheduler started successfully!\n"
            f"   📅 Interval: Every {interval} minutes\n"
            "   📋 Job: Check and send follow-up reminders\n"
            "   ⏱️  Status: Running in background"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start reminder scheduler: {str(e)}", exc_info=True)
        scheduler = None


def stop_scheduler():
    """
    Gracefully stop the background scheduler.
    
    Call this if you need to stop the reminder service:
    - During shutdown
    - During maintenance
    - For debugging
    
    Example:
        from Anand_Clinic.scheduler import stop_scheduler
        stop_scheduler()
    """
    global scheduler
    
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown(wait=True)
            logger.info("✅ Reminder scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
    else:
        logger.warning("⚠️  Scheduler is not running")


def get_scheduler_status():
    """
    Get the current status of the scheduler.
    
    Returns:
        dict: Status information including:
            - 'running' (bool): Is scheduler currently running?
            - 'job_count' (int): Number of scheduled jobs
            - 'jobs' (list): List of job details
    
    Example:
        from Anand_Clinic.scheduler import get_scheduler_status
        status = get_scheduler_status()
        print(f"Scheduler running: {status['running']}")
    """
    if scheduler is None:
        return {
            'running': False,
            'job_count': 0,
            'jobs': []
        }
    
    return {
        'running': scheduler.running,
        'job_count': len(scheduler.get_jobs()),
        'jobs': [
            {
                'id': job.id,
                'name': job.name,
                'next_run_time': str(job.next_run_time)
            }
            for job in scheduler.get_jobs()
        ]
    }
