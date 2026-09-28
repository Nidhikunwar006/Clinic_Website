"""
Example Implementation Patterns for WhatsApp Reminder Service

This file contains ready-to-use code examples for various scenarios.
Copy and adapt these examples to your needs.
"""

# ============================================================================
# EXAMPLE 1: Send a test reminder to yourself
# ============================================================================

def example_1_send_test_reminder():
    """
    Send a test reminder to your own number to verify WhatsApp is working.
    
    Use this to validate that your WhatsApp credentials are correct
    before setting up automatic reminders.
    """
    from reminder_service import send_whatsapp_reminder
    
    # Replace with your actual phone number
    YOUR_PHONE = "919876543210"  # Country code + 10 digits
    TEST_MESSAGE = (
        "Hello! 👋\n\n"
        "This is a test message from your clinic's reminder system.\n"
        "If you received this, WhatsApp is properly configured! ✅\n\n"
        "You can now set up automatic appointment reminders."
    )
    
    print("📤 Sending test message...")
    result = send_whatsapp_reminder(YOUR_PHONE, TEST_MESSAGE)
    
    if result['success']:
        print(f"✅ Success! Message ID: {result['message_id']}")
        print("WhatsApp credentials are working correctly.")
    else:
        print(f"❌ Failed: {result['error']}")
        print("Check your WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env file")
    
    return result


# ============================================================================
# EXAMPLE 2: Check and send reminders in dry-run mode
# ============================================================================

def example_2_dry_run_check():
    """
    See what reminders would be sent without actually sending them.
    
    Use this to test your reminder logic before enabling actual sending.
    """
    from reminder_service import check_and_send_followup_reminders
    
    print("🧪 Running reminder check in DRY-RUN mode...")
    print("This will show what would be sent WITHOUT actually sending.\n")
    
    # Run check without sending
    stats = check_and_send_followup_reminders(batch_size=10, dry_run=True)
    
    # Display results
    print("\n" + "="*50)
    print("📊 DRY-RUN RESULTS")
    print("="*50)
    print(f"Follow-ups checked: {stats['total_processed']}")
    print(f"Would send to: {stats['reminders_sent']} patients")
    print(f"Dry-run mode: {stats['dry_run']}")
    
    if stats['errors']:
        print(f"\n⚠️  Errors encountered:")
        for i, error in enumerate(stats['errors'], 1):
            print(f"  {i}. {error}")
    
    return stats


# ============================================================================
# EXAMPLE 3: Actually send reminders with confirmation
# ============================================================================

def example_3_send_reminders_with_confirmation():
    """
    Send reminders with a confirmation prompt.
    
    Use this when you want to manually confirm before sending real reminders.
    """
    from reminder_service import check_and_send_followup_reminders
    
    print("📤 Reminder Sending Mode\n")
    
    # First, do a dry-run to see what would be sent
    print("Step 1: Checking what would be sent...")
    preview_stats = check_and_send_followup_reminders(batch_size=10, dry_run=True)
    
    print(f"\n✅ Found {preview_stats['reminders_sent']} reminders to send\n")
    
    # Ask for confirmation
    confirm = input("Do you want to actually send these reminders? (yes/no): ").lower()
    
    if confirm in ['yes', 'y']:
        print("\n📤 Sending reminders...")
        actual_stats = check_and_send_followup_reminders(batch_size=10, dry_run=False)
        
        print(f"\n✅ Success!")
        print(f"  Sent to: {actual_stats['reminders_sent']} patients")
        print(f"  Failed: {actual_stats['reminders_failed']}")
        
        if actual_stats['errors']:
            print(f"\n⚠️  Errors:")
            for error in actual_stats['errors']:
                print(f"  - {error}")
        
        return actual_stats
    else:
        print("\n❌ Cancelled. No reminders were sent.")
        return None


# ============================================================================
# EXAMPLE 4: Send reminder to a specific patient
# ============================================================================

def example_4_send_reminder_to_specific_patient(patient_id: int):
    """
    Send a reminder to a specific patient.
    
    Use this to manually send reminders for specific patients.
    
    Args:
        patient_id (int): The patient's case_no
    """
    from Anand_Clinic.models import Patient, FollowUp
    from reminder_service import send_whatsapp_reminder
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        # Get the patient
        patient = Patient.objects.get(case_no=patient_id)
        print(f"📋 Found patient: {patient.name}")
        
        # Find their scheduled follow-up
        followup = FollowUp.objects.filter(
            patient=patient,
            status='scheduled'
        ).first()
        
        if not followup:
            print(f"❌ No scheduled follow-up found for {patient.name}")
            return None
        
        # Format phone number
        country_code = patient.profile.country_code if hasattr(patient, 'profile') else '91'
        phone_number = f"{country_code}{patient.phone_no}"
        
        # Create personalized message
        appointment_time = followup.scheduled_date.strftime("%d %B %Y at %I:%M %p")
        message = (
            f"Dear {patient.name},\n\n"
            f"📅 Reminder: Your follow-up appointment is scheduled for:\n"
            f"🕐 {appointment_time}\n"
            f"👨‍⚕️ Doctor: {patient.get_doctor_display()}\n\n"
            f"Please arrive on time. Contact us if you need to reschedule.\n\n"
            f"Thank you,\nAnand Clinic"
        )
        
        # Send the reminder
        print(f"\n📤 Sending reminder to {patient.name} ({phone_number})...")
        result = send_whatsapp_reminder(phone_number, message)
        
        if result['success']:
            # Update the database
            followup.reminder_sent = True
            followup.save()
            print(f"✅ Reminder sent successfully!")
            print(f"   Message ID: {result['message_id']}")
            return result
        else:
            print(f"❌ Failed: {result['error']}")
            return result
    
    except Patient.DoesNotExist:
        print(f"❌ Patient with ID {patient_id} not found")
        return None


# ============================================================================
# EXAMPLE 5: View reminder statistics
# ============================================================================

def example_5_view_reminder_statistics():
    """
    View statistics about reminders sent to patients.
    
    Shows how many reminders have been sent, how many are pending, etc.
    """
    from Anand_Clinic.models import FollowUp
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    
    # Get statistics
    total_scheduled = FollowUp.objects.filter(status='scheduled').count()
    reminders_sent = FollowUp.objects.filter(status='scheduled', reminder_sent=True).count()
    reminders_pending = FollowUp.objects.filter(status='scheduled', reminder_sent=False).count()
    
    # Get upcoming reminders (within 24 hours)
    upcoming_24h = FollowUp.objects.filter(
        status='scheduled',
        scheduled_date__gte=now,
        scheduled_date__lte=now + timedelta(hours=24),
        reminder_sent=False
    ).count()
    
    # Display statistics
    print("\n" + "="*60)
    print("📊 REMINDER SERVICE STATISTICS")
    print("="*60)
    print(f"\n📋 Total scheduled follow-ups: {total_scheduled}")
    print(f"✅ Reminders already sent: {reminders_sent}")
    print(f"⏳ Reminders still pending: {reminders_pending}")
    print(f"🔔 Need reminder in next 24h: {upcoming_24h}")
    
    # Calculate percentages
    if total_scheduled > 0:
        sent_percent = (reminders_sent / total_scheduled) * 100
        pending_percent = (reminders_pending / total_scheduled) * 100
        print(f"\n📈 Coverage: {sent_percent:.1f}% reminders sent")
    
    print("\n" + "="*60)
    
    return {
        'total': total_scheduled,
        'sent': reminders_sent,
        'pending': reminders_pending,
        'upcoming_24h': upcoming_24h
    }


# ============================================================================
# EXAMPLE 6: Scheduler status and control
# ============================================================================

def example_6_scheduler_management():
    """
    Check scheduler status and control it.
    
    View running jobs, start/stop scheduler, etc.
    """
    from Anand_Clinic.scheduler import (
        get_scheduler_status, 
        start_scheduler, 
        stop_scheduler
    )
    
    # Get current status
    status = get_scheduler_status()
    
    print("\n" + "="*60)
    print("⏱️  REMINDER SCHEDULER STATUS")
    print("="*60)
    print(f"Status: {'✅ Running' if status['running'] else '❌ Stopped'}")
    print(f"Active jobs: {status['job_count']}")
    
    if status['jobs']:
        print("\n📋 Scheduled Jobs:")
        for job in status['jobs']:
            print(f"  • {job['name']}")
            print(f"    ID: {job['id']}")
            print(f"    Next run: {job['next_run_time']}")
    
    print("\n" + "="*60)
    
    # Example: Restart scheduler if not running
    if not status['running']:
        print("\n⚠️  Scheduler is not running. Starting it now...")
        start_scheduler()
        new_status = get_scheduler_status()
        print(f"✅ Scheduler started: {new_status['running']}")
    
    return status


# ============================================================================
# EXAMPLE 7: Integration with Django views
# ============================================================================

def example_7_django_view_integration():
    """
    Example Django view to trigger reminders from your web interface.
    
    Add this to your Anand_Clinic/views.py:
    """
    
    # Copy this code to your views.py file
    view_code = '''
    from django.shortcuts import render
    from django.contrib.auth.decorators import login_required
    from django.http import JsonResponse
    from reminder_service import check_and_send_followup_reminders
    
    
    @login_required
    def send_reminders_view(request):
        """
        Web view to manually trigger reminder sending.
        
        GET request with dry_run=true for preview
        GET request with dry_run=false to actually send
        """
        
        # Only allow receptionist and doctor roles
        if not hasattr(request.user, 'profile') or request.user.profile.role not in ['doctor', 'receptionist']:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get parameters
        dry_run = request.GET.get('dry_run', 'true').lower() == 'true'
        batch_size = int(request.GET.get('batch_size', 10))
        
        # Run reminder check
        stats = check_and_send_followup_reminders(batch_size=batch_size, dry_run=dry_run)
        
        return JsonResponse({
            'success': True,
            'mode': 'dry-run' if stats['dry_run'] else 'sending',
            'total_checked': stats['total_processed'],
            'reminders_sent': stats['reminders_sent'],
            'reminders_failed': stats['reminders_failed'],
            'errors': stats['errors']
        })
    
    
    # Add to your urls.py:
    # path('api/send-reminders/', send_reminders_view, name='send_reminders'),
    '''
    
    print("Example Django View Code:")
    print(view_code)
    return view_code


# ============================================================================
# EXAMPLE 8: Logging and monitoring
# ============================================================================

def example_8_setup_logging():
    """
    Example Django logging configuration for reminder service.
    
    Add this to your Clinic/settings.py:
    """
    
    logging_config = '''
    # In Clinic/settings.py:
    
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {message}',
                'style': '{',
            },
        },
        'handlers': {
            'file': {
                'level': 'INFO',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/reminder_service.log',
                'maxBytes': 1024*1024*10,  # 10MB
                'backupCount': 5,
                'formatter': 'verbose',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
        },
        'loggers': {
            'reminder_service': {
                'handlers': ['file', 'console'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    '''
    
    print("Example Logging Configuration:")
    print(logging_config)
    return logging_config


# ============================================================================
# EXAMPLE 9: Testing the service
# ============================================================================

def example_9_run_tests():
    """
    Run the test suite for the reminder service.
    
    Run from command line:
    """
    
    commands = """
    # Run all reminder service tests
    python manage.py test Anand_Clinic.tests_reminder_service -v 2
    
    # Run specific test class
    python manage.py test Anand_Clinic.tests_reminder_service.WhatsAppReminderServiceTestCase -v 2
    
    # Run specific test method
    python manage.py test Anand_Clinic.tests_reminder_service.WhatsAppReminderServiceTestCase.test_send_whatsapp_reminder_success -v 2
    """
    
    print("Test Commands:")
    print(commands)
    return commands


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Run examples from command line.
    
    python reminder_examples.py
    """
    
    print("\n" + "="*70)
    print("🎯 WHATSAPP REMINDER SERVICE - IMPLEMENTATION EXAMPLES")
    print("="*70)
    
    print("\n" + "Available examples:")
    print("  1. Send test reminder to yourself")
    print("  2. Check reminders (dry-run)")
    print("  3. Send reminders with confirmation")
    print("  4. Send reminder to specific patient")
    print("  5. View reminder statistics")
    print("  6. Scheduler management")
    print("  7. Django view integration (code only)")
    print("  8. Logging setup (code only)")
    print("  9. Run tests")
    
    choice = input("\nSelect an example (1-9) or 'q' to quit: ").strip()
    
    if choice == '1':
        example_1_send_test_reminder()
    elif choice == '2':
        example_2_dry_run_check()
    elif choice == '3':
        example_3_send_reminders_with_confirmation()
    elif choice == '4':
        patient_id = input("Enter patient ID: ")
        example_4_send_reminder_to_specific_patient(int(patient_id))
    elif choice == '5':
        example_5_view_reminder_statistics()
    elif choice == '6':
        example_6_scheduler_management()
    elif choice == '7':
        example_7_django_view_integration()
    elif choice == '8':
        example_8_setup_logging()
    elif choice == '9':
        example_9_run_tests()
    elif choice.lower() == 'q':
        print("Goodbye!")
    else:
        print("Invalid choice!")
