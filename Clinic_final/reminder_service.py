"""
Reminder Service Module for WhatsApp Follow-up Reminders

This module handles the automated sending of WhatsApp reminders to patients
for their scheduled follow-up appointments. It checks for upcoming follow-ups
that are within 24 hours and sends reminders to patients who haven't received
them yet.

The system is designed to be modular and testable:
- Core WhatsApp sending logic is separated from the reminder check logic
- All WhatsApp credentials are loaded from environment variables
- Boolean flag 'reminder_sent' tracks whether a reminder has been sent
- Background task runner handles continuous checking without overloading the server

Author: Clinic Management System
Date: January 2026
"""

import os
import logging
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from dotenv import load_dotenv

# Configure logging for tracking reminder operations
logger = logging.getLogger(__name__)
load_dotenv()

# Load WhatsApp Cloud API credentials from environment variables
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")


def send_whatsapp_reminder_demo(patient_phone_number: str, reminder_message: str) -> dict:
    """
    DEMO MODE function: Simulates sending a WhatsApp reminder without calling the API.
    
    This function is useful for testing the reminder system without:
    - WhatsApp API credentials (WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID)
    - Actually sending messages to patients
    - Making network requests
    
    It returns a successful response as if the message was sent.
    
    Args:
        patient_phone_number (str): Patient's phone number (e.g., "91XXXXXXXXXX")
        reminder_message (str): The message that would be sent
    
    Returns:
        dict: A successful response dictionary (simulated)
    
    Example:
        result = send_whatsapp_reminder_demo("919876543210", "Your appointment is tomorrow")
        # Returns: {'success': True, 'message_id': 'demo_xxx', ...}
    """
    # Generate a fake message ID for demo purposes
    demo_message_id = f"demo_{patient_phone_number}_{int(timezone.now().timestamp())}"
    
    logger.info(
        f"🧪 [DEMO MODE] Message would be sent to {patient_phone_number}\n"
        f"   Message ID (simulated): {demo_message_id}"
    )
    
    return {
        'success': True,
        'status_code': 200,
        'message_id': demo_message_id,
        'error': None,
        'response': {'messages': [{'id': demo_message_id}]},
        'demo_mode': True
    }


def send_whatsapp_reminder(patient_phone_number: str, reminder_message: str) -> dict:
    """
    Core function to send a WhatsApp reminder message to a patient.
    
    This is a LOW-LEVEL function that handles the actual API call to WhatsApp Cloud API.
    It's separated from the business logic to ensure modularity and easy testing.
    
    Args:
        patient_phone_number (str): Patient's phone number in format: "91XXXXXXXXXX" 
                                   (country code + number, no special characters)
        reminder_message (str): The reminder message text to send to the patient
    
    Returns:
        dict: A dictionary containing:
            - 'success' (bool): Whether the message was sent successfully
            - 'status_code' (int): HTTP status code from the API
            - 'message_id' (str): WhatsApp message ID if successful, None otherwise
            - 'error' (str): Error message if failed, None if successful
            - 'response' (dict): Full API response for debugging purposes
    
    Raises:
        RuntimeError: If WhatsApp API credentials are missing from environment variables
    
    Example:
        result = send_whatsapp_reminder("919876543210", "Your appointment is tomorrow at 10 AM")
        if result['success']:
            print(f"Message sent with ID: {result['message_id']}")
        else:
            print(f"Failed: {result['error']}")
    """
    
    # Validate that all required WhatsApp credentials are configured
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        error_msg = (
            "❌ Missing WhatsApp API Credentials!\n"
            "Please configure WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env file"
        )
        logger.error(error_msg)
        return {
            'success': False,
            'status_code': None,
            'message_id': None,
            'error': error_msg,
            'response': None
        }
    
    # Validate phone number format (basic validation)
    if not patient_phone_number or len(patient_phone_number) < 10:
        error_msg = f"❌ Invalid phone number format: {patient_phone_number}"
        logger.error(error_msg)
        return {
            'success': False,
            'status_code': None,
            'message_id': None,
            'error': error_msg,
            'response': None
        }
    
    try:
        # Construct the WhatsApp Cloud API endpoint URL
        url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
        
        # Set up request headers with authorization token
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # Build the message payload following WhatsApp Cloud API specifications
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": patient_phone_number,  # e.g., "91XXXXXXXXXX"
            "type": "text",
            "text": {
                "preview_url": False,
                "body": reminder_message
            }
        }
        
        # Send the HTTP POST request to WhatsApp Cloud API
        logger.info(f"📤 Sending WhatsApp reminder to {patient_phone_number}")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # Parse the API response
        response_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
        
        # Check if the message was sent successfully (HTTP 200)
        if response.status_code == 200:
            message_id = response_data.get('messages', [{}])[0].get('id', 'unknown')
            logger.info(f"✅ WhatsApp reminder sent successfully to {patient_phone_number} (ID: {message_id})")
            
            return {
                'success': True,
                'status_code': response.status_code,
                'message_id': message_id,
                'error': None,
                'response': response_data
            }
        else:
            # Handle API errors (rate limit, invalid number, etc.)
            error_msg = response_data.get('error', {}).get('message', f'HTTP {response.status_code}')
            logger.warning(f"⚠️ Failed to send WhatsApp reminder to {patient_phone_number}: {error_msg}")
            
            return {
                'success': False,
                'status_code': response.status_code,
                'message_id': None,
                'error': error_msg,
                'response': response_data
            }
    
    except requests.exceptions.Timeout:
        error_msg = "❌ Request timeout - WhatsApp API not responding"
        logger.error(error_msg)
        return {
            'success': False,
            'status_code': None,
            'message_id': None,
            'error': error_msg,
            'response': None
        }
    
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Network error sending WhatsApp reminder: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'status_code': None,
            'message_id': None,
            'error': error_msg,
            'response': None
        }
    
    except Exception as e:
        error_msg = f"❌ Unexpected error sending WhatsApp reminder: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'status_code': None,
            'message_id': None,
            'error': error_msg,
            'response': None
        }


def check_and_send_followup_reminders(batch_size: int = 10, dry_run: bool = False, demo_mode: bool = False) -> dict:
    """
    HIGH-LEVEL function that identifies patients needing reminders and sends them.
    
    This is the MAIN BUSINESS LOGIC function that:
    1. Queries the database for scheduled follow-ups
    2. Filters for follow-ups scheduled within the next 24 hours
    3. Excludes follow-ups that already had reminders sent
    4. Sends WhatsApp reminders to eligible patients
    5. Marks reminders as sent in the database
    
    Args:
        batch_size (int, optional): Maximum number of reminders to send in one run.
                                   Defaults to 10 to avoid server overload.
                                   Increase this if you have many patients.
        
        dry_run (bool, optional): If True, identifies reminders to send but doesn't 
                                 actually send them. Useful for testing and logging.
                                 Defaults to False.
        
        demo_mode (bool, optional): If True, uses a simulated WhatsApp sender (no API call).
                                   Updates database as if messages were sent.
                                   Useful for testing without WhatsApp credentials.
                                   Defaults to False.
    
    Returns:
        dict: Summary statistics of the reminder operation containing:
            - 'total_processed' (int): Number of follow-ups checked
            - 'reminders_sent' (int): Number of reminders successfully sent
            - 'reminders_failed' (int): Number of reminders that failed
            - 'reminders_skipped' (int): Number of follow-ups already having reminders
            - 'dry_run' (bool): Whether this was a dry run
            - 'demo_mode' (bool): Whether demo mode was used
            - 'errors' (list): List of error messages encountered
    
    Example:
        # Normal operation - actually send reminders
        stats = check_and_send_followup_reminders(batch_size=10)
        print(f"Sent {stats['reminders_sent']} reminders")
        
        # Test run - see what would be sent without actually sending
        stats = check_and_send_followup_reminders(batch_size=10, dry_run=True)
        
        # Demo mode - simulate sending and update database
        stats = check_and_send_followup_reminders(batch_size=10, demo_mode=True)
    """
    
    from Anand_Clinic.models import FollowUp, Patient
    
    # Initialize statistics dictionary to track operation results
    stats = {
        'total_processed': 0,
        'reminders_sent': 0,
        'reminders_failed': 0,
        'reminders_skipped': 0,
        'dry_run': dry_run,
        'demo_mode': demo_mode,
        'errors': []
    }
    
    try:
        # Get current time for comparison
        now = timezone.now()
        
        # Calculate the 24-hour window: now to now + 24 hours
        # This identifies follow-ups that need reminders in the next 24 hours
        remind_start_time = now
        remind_end_time = now + timedelta(hours=24)
        
        logger.info(
            f"\n🔍 CHECKING FOR FOLLOW-UPS\n"
            f"   Time window: {remind_start_time.strftime('%Y-%m-%d %H:%M:%S')} to {remind_end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   Batch size: {batch_size} | Demo: {demo_mode} | Dry run: {dry_run}\n"
        )
        
        # QUERY 1: Find all SCHEDULED follow-ups that need reminders in the next 24 hours
        # Filter criteria:
        # - status='scheduled': Only follow-ups that haven't been completed/missed/cancelled
        # - scheduled_date >= now: Follow-up hasn't passed yet
        # - scheduled_date <= now + 24h: Follow-up is within next 24 hours
        # - reminder_sent=False: Reminder hasn't been sent yet
        followups_needing_reminders = FollowUp.objects.filter(
            status='scheduled',
            scheduled_date__gte=remind_start_time,
            scheduled_date__lte=remind_end_time,
            reminder_sent=False
        ).select_related('patient')[:batch_size]  # Limit batch size to avoid overload
        
        stats['total_processed'] = followups_needing_reminders.count()
        
        if stats['total_processed'] > 0:
            logger.info(f"\n{'='*70}")
            logger.info(f"📋 FOUND {stats['total_processed']} FOLLOW-UP(S) NEEDING REMINDER(S)")
            logger.info(f"{'='*70}\n")
        else:
            logger.info(f"📋 No follow-ups needing reminders at this time\n")
        
        # PROCESS EACH FOLLOW-UP: Send reminders and update database
        for followup in followups_needing_reminders:
            try:
                patient = followup.patient
                
                # Verify patient phone number exists and is valid
                if not patient.phone_no or len(patient.phone_no) < 10:
                    error_msg = (
                        f"⚠️ Patient {patient.name} (ID: {patient.case_no}) has invalid phone number: "
                        f"{patient.phone_no}"
                    )
                    logger.warning(error_msg)
                    stats['errors'].append(error_msg)
                    stats['reminders_failed'] += 1
                    continue
                
                # Format phone number with country code (default: India +91)
                # The phone_no field stores only the 10-digit number, so we prepend country code
                country_code = patient.profile.country_code if hasattr(patient, 'profile') else '91'
                formatted_phone = f"{country_code}{patient.phone_no}"
                
                # Create a personalized reminder message
                # This message will be sent to the patient as the reminder
                appointment_time = followup.scheduled_date.strftime("%d %B %Y at %I:%M %p")
                reminder_message = (
                    f"Dear {patient.name},\n\n"
                    f"📅 This is a gentle reminder about your follow-up appointment:\n"
                    f"🕐 Scheduled for: {appointment_time}\n"
                    f"👨‍⚕️ Doctor: {patient.get_doctor_display()}\n\n"
                    f"Please arrive on time. If you need to reschedule, contact the clinic.\n\n"
                    f"Thank you,\n"
                    f"Anand Clinic"
                )
                
                # DRY RUN MODE: Log what would be sent without actually sending
                if dry_run:
                    logger.info(
                        f"🧪 [DRY RUN] Would send reminder to {patient.name} ({formatted_phone}):\n"
                        f"   Message: {reminder_message[:50]}...\n"
                        f"   Scheduled: {appointment_time}"
                    )
                    stats['reminders_sent'] += 1
                
                # DEMO MODE: Send using dummy function, then update database
                elif demo_mode:
                    # Use demo sender that doesn't call API
                    result = send_whatsapp_reminder_demo(formatted_phone, reminder_message)
                    
                    if result['success']:
                        # ✅ Success: Update the reminder_sent flag in the database
                        followup.reminder_sent = True
                        followup.save(update_fields=['reminder_sent'])
                        
                        # Print to terminal and log the full message
                        logger.info(
                            f"\n{'='*70}\n"
                            f"✅ DEMO: Reminder marked as sent to {patient.name}\n"
                            f"{'='*70}\n"
                            f"📱 Phone: {formatted_phone}\n"
                            f"📅 Appointment: {appointment_time}\n"
                            f"💬 Message:\n"
                            f"{'-'*70}\n"
                            f"{reminder_message}\n"
                            f"{'-'*70}\n"
                            f"Message ID (simulated): {result['message_id']}\n"
                            f"Database: reminder_sent = True ✓\n"
                            f"{'='*70}\n"
                        )
                        stats['reminders_sent'] += 1
                    else:
                        error_msg = f"⚠️ Demo mode failed for {patient.name}: {result.get('error')}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
                        stats['reminders_failed'] += 1
                
                else:
                    # ACTUAL MODE: Send the WhatsApp reminder using the low-level function
                    result = send_whatsapp_reminder(formatted_phone, reminder_message)
                    
                    if result['success']:
                        # ✅ Success: Update the reminder_sent flag in the database
                        followup.reminder_sent = True
                        followup.save(update_fields=['reminder_sent'])
                        
                        logger.info(
                            f"✅ Reminder sent to {patient.name} ({formatted_phone}) "
                            f"[Message ID: {result['message_id']}]"
                        )
                        stats['reminders_sent'] += 1
                    else:
                        # ❌ Failed: Log the error but continue with other patients
                        error_msg = (
                            f"⚠️ Failed to send reminder to {patient.name} ({formatted_phone}): "
                            f"{result['error']}"
                        )
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)
                        stats['reminders_failed'] += 1
            
            except ObjectDoesNotExist as e:
                # Handle case where related object doesn't exist
                error_msg = (
                    f"⚠️ Data integrity issue with follow-up ID {followup.id}: "
                    f"Related patient record not found"
                )
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                stats['reminders_failed'] += 1
            
            except Exception as e:
                # Catch any other unexpected errors and continue
                error_msg = (
                    f"⚠️ Unexpected error processing follow-up ID {followup.id}: {str(e)}"
                )
                logger.error(error_msg, exc_info=True)
                stats['errors'].append(error_msg)
                stats['reminders_failed'] += 1
        
        # Log final summary
        logger.info(
            f"\n📊 Reminder Run Summary:\n"
            f"   Total checked: {stats['total_processed']}\n"
            f"   Successfully sent: {stats['reminders_sent']}\n"
            f"   Failed: {stats['reminders_failed']}\n"
            f"   Dry run: {stats['dry_run']}"
        )
        
        return stats
    
    except Exception as e:
        error_msg = f"❌ Critical error in reminder check function: {str(e)}"
        logger.critical(error_msg, exc_info=True)
        stats['errors'].append(error_msg)
        return stats


def run_reminder_scheduler():
    """
    BACKGROUND TASK function to continuously check for reminders without overloading the server.
    
    This function is designed to be run by a background task scheduler (like APScheduler,
    Celery, or Django management commands run on a schedule).
    
    The scheduler calls this function periodically (recommended: every 15-30 minutes) to:
    1. Check for follow-ups within 24 hours that need reminders
    2. Send reminders only if not already sent
    3. Log all operations for auditing purposes
    4. Handle errors gracefully without stopping other operations
    
    SETUP INSTRUCTIONS for continuous background execution:
    
    Option 1: Using APScheduler (Recommended for simple setups)
    --------------------------------------------------------
    1. Install: pip install django-apscheduler
    2. Add to INSTALLED_APPS in settings.py: 'django_apscheduler'
    3. Create a management command (see instructions below)
    4. Run: python manage.py apscheduler
    
    Option 2: Using Celery (Recommended for production)
    ---------------------------------------------------
    1. Install: pip install celery celery-beat
    2. Configure CELERY settings in settings.py
    3. Create a Celery task decorator above this function
    4. Run: celery -A Clinic worker -B
    
    Option 3: Using APScheduler in Django Apps (Manual setup)
    ---------------------------------------------------------
    Add this to your Django app's apps.py ready() method:
    
        from apscheduler.schedulers.background import BackgroundScheduler
        from reminder_service import run_reminder_scheduler
        
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_reminder_scheduler, 'interval', minutes=15)
        scheduler.start()
    
    Returns:
        dict: Same statistics dict as check_and_send_followup_reminders()
    """
    
    logger.info("⏱️ Starting scheduled reminder check...")
    
    try:
        # Call the main reminder logic with a conservative batch size
        # Batch size of 10 means max 10 reminders per run = light server load
        # Increase if you have many patients and run less frequently
        stats = check_and_send_followup_reminders(batch_size=10, dry_run=False)
        
        logger.info("✅ Reminder scheduler completed successfully")
        return stats
    
    except Exception as e:
        logger.critical(f"❌ Reminder scheduler encountered critical error: {str(e)}", exc_info=True)
        return {
            'total_processed': 0,
            'reminders_sent': 0,
            'reminders_failed': 0,
            'reminders_skipped': 0,
            'dry_run': False,
            'errors': [str(e)]
        }


# ============================================================================
# MANAGEMENT COMMAND SETUP (for running reminders from command line)
# ============================================================================
# 
# To use this with Django management commands:
# 
# 1. Create: Anand_Clinic/management/commands/send_reminders.py
# 
# 2. Add this content to the file:
# 
#    from django.core.management.base import BaseCommand
#    from reminder_service import run_reminder_scheduler, check_and_send_followup_reminders
#    
#    class Command(BaseCommand):
#        help = 'Send follow-up reminders to patients'
#        
#        def add_arguments(self, parser):
#            parser.add_argument(
#                '--dry-run',
#                action='store_true',
#                help='Show what would be sent without actually sending',
#            )
#        
#        def handle(self, *args, **options):
#            dry_run = options.get('dry_run', False)
#            stats = check_and_send_followup_reminders(batch_size=10, dry_run=dry_run)
#            self.stdout.write(f"Processed: {stats['total_processed']}")
#            self.stdout.write(f"Sent: {stats['reminders_sent']}")
#            self.stdout.write(f"Failed: {stats['reminders_failed']}")
# 
# 3. Run manually:
#    python manage.py send_reminders         # Actually send reminders
#    python manage.py send_reminders --dry-run  # Test without sending
# 
# 4. Run on a schedule using cron (Linux/Mac):
#    */15 * * * * cd /path/to/clinic && python manage.py send_reminders
#    (This runs every 15 minutes)
# 
# ============================================================================
