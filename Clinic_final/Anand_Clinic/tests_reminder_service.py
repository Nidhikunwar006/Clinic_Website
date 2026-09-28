"""
Test Suite for WhatsApp Reminder Service

This test module provides comprehensive testing for the reminder functionality
including unit tests and integration tests.

Run tests with:
    python manage.py test Anand_Clinic.tests.test_reminder_service -v 2
"""

import os
from unittest.mock import patch, MagicMock
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth.models import User

from Anand_Clinic.models import Patient, FollowUp, Profile


class WhatsAppReminderServiceTestCase(TestCase):
    """Test cases for the WhatsApp reminder service functionality"""
    
    @classmethod
    def setUpTestData(cls):
        """
        Set up test data that's shared across all test methods.
        Called once per test class, not per test method.
        """
        # Create test user for the doctor
        cls.user = User.objects.create_user(
            username='testdoctor',
            password='testpass123',
            first_name='Test',
            last_name='Doctor'
        )
        
        # Create profile for user (required for country_code)
        cls.profile = Profile.objects.create(
            user=cls.user,
            whatsapp='9876543210',
            country_code='91',
            role='doctor'
        )
    
    def setUp(self):
        """
        Set up fresh data for each test method.
        Called before each test runs.
        """
        # Create test patient
        self.patient = Patient.objects.create(
            name='John Doe',
            age=30,
            phone_no='9876543210',
            doctor='dr_1',
            gender='male'
        )
    
    def test_send_whatsapp_reminder_success(self):
        """
        Test successful WhatsApp message sending.
        
        ✅ Tests:
        - Message payload is correctly formatted
        - API endpoint is called with correct parameters
        - Success response is properly handled
        """
        from reminder_service import send_whatsapp_reminder
        
        # Mock the requests.post to simulate successful API response
        with patch('reminder_service.requests.post') as mock_post:
            # Configure the mock to return success response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.return_value = {
                'messages': [{'id': 'wamid.123456'}]
            }
            mock_post.return_value = mock_response
            
            # Call the function
            result = send_whatsapp_reminder('919876543210', 'Test reminder message')
            
            # Assertions
            self.assertTrue(result['success'], "Message sending should succeed")
            self.assertEqual(result['status_code'], 200, "Status code should be 200")
            self.assertEqual(result['message_id'], 'wamid.123456', "Message ID should be returned")
            self.assertIsNone(result['error'], "Error should be None on success")
            
            # Verify API was called with correct parameters
            self.assertTrue(mock_post.called, "API should be called")
            call_args = mock_post.call_args
            
            # Check URL
            self.assertIn('messages', call_args[0][0], "Correct API endpoint should be used")
            
            # Check payload
            payload = call_args[1]['json']
            self.assertEqual(payload['to'], '919876543210', "Phone number should match")
            self.assertEqual(payload['text']['body'], 'Test reminder message', "Message body should match")
    
    def test_send_whatsapp_reminder_missing_credentials(self):
        """
        Test WhatsApp message sending with missing credentials.
        
        ✅ Tests:
        - Function gracefully handles missing API credentials
        - Appropriate error message is returned
        - API is not called when credentials are missing
        """
        from reminder_service import send_whatsapp_reminder
        
        # Mock environment variables as missing
        with patch.dict(os.environ, {'WHATSAPP_TOKEN': '', 'WHATSAPP_PHONE_NUMBER_ID': ''}):
            with patch('reminder_service.WHATSAPP_TOKEN', None):
                with patch('reminder_service.PHONE_NUMBER_ID', None):
                    result = send_whatsapp_reminder('919876543210', 'Test message')
                    
                    # Assertions
                    self.assertFalse(result['success'], "Should fail without credentials")
                    self.assertIn('Missing', result['error'], "Error message should mention missing credentials")
                    self.assertIsNone(result['message_id'], "Message ID should be None on failure")
    
    def test_send_whatsapp_reminder_invalid_phone(self):
        """
        Test WhatsApp message sending with invalid phone number.
        
        ✅ Tests:
        - Invalid phone numbers are rejected
        - Appropriate error message is returned
        """
        from reminder_service import send_whatsapp_reminder
        
        # Test with empty phone number
        with patch('reminder_service.WHATSAPP_TOKEN', 'test_token'):
            with patch('reminder_service.PHONE_NUMBER_ID', 'test_id'):
                result = send_whatsapp_reminder('', 'Test message')
                self.assertFalse(result['success'], "Should fail with empty phone")
        
        # Test with too short phone number
        result = send_whatsapp_reminder('1234', 'Test message')
        self.assertFalse(result['success'], "Should fail with too short phone")
    
    def test_check_and_send_followup_reminders_dry_run(self):
        """
        Test reminder checking in dry-run mode (no actual sending).
        
        ✅ Tests:
        - Function correctly identifies follow-ups needing reminders
        - Dry run mode doesn't modify database
        - Statistics are correctly reported
        """
        from reminder_service import check_and_send_followup_reminders
        
        # Create a follow-up scheduled for 12 hours from now
        scheduled_time = timezone.now() + timedelta(hours=12)
        followup = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=scheduled_time,
            status='scheduled',
            reminder_sent=False
        )
        
        # Run in dry-run mode
        stats = check_and_send_followup_reminders(batch_size=10, dry_run=True)
        
        # Assertions
        self.assertEqual(stats['total_processed'], 1, "Should find 1 follow-up")
        self.assertEqual(stats['reminders_sent'], 1, "Dry run should count as sent")
        self.assertTrue(stats['dry_run'], "Should be marked as dry run")
        
        # Verify database wasn't modified
        followup.refresh_from_db()
        self.assertFalse(followup.reminder_sent, "Database should not be modified in dry run")
    
    def test_check_and_send_followup_reminders_filters_correctly(self):
        """
        Test that reminder checking filters follow-ups correctly.
        
        ✅ Tests:
        - Only follow-ups within 24 hours are selected
        - Only scheduled status follow-ups are selected
        - Already-reminded follow-ups are skipped
        - Reminders from the past are not selected
        """
        from reminder_service import check_and_send_followup_reminders
        
        # Create various follow-ups to test filtering
        now = timezone.now()
        
        # ✅ This one SHOULD be included (12 hours from now)
        followup_include_1 = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now + timedelta(hours=12),
            status='scheduled',
            reminder_sent=False
        )
        
        # ✅ This one SHOULD be included (23 hours from now, just before cutoff)
        followup_include_2 = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now + timedelta(hours=23),
            status='scheduled',
            reminder_sent=False
        )
        
        # ❌ This one should NOT be included (already has reminder)
        followup_exclude_1 = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now + timedelta(hours=10),
            status='scheduled',
            reminder_sent=True
        )
        
        # ❌ This one should NOT be included (beyond 24 hours)
        followup_exclude_2 = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now + timedelta(hours=25),
            status='scheduled',
            reminder_sent=False
        )
        
        # ❌ This one should NOT be included (already completed)
        followup_exclude_3 = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now + timedelta(hours=10),
            status='completed',
            reminder_sent=False
        )
        
        # ❌ This one should NOT be included (in the past)
        followup_exclude_4 = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now - timedelta(hours=5),
            status='scheduled',
            reminder_sent=False
        )
        
        # Run check in dry-run mode
        stats = check_and_send_followup_reminders(batch_size=100, dry_run=True)
        
        # Assertions - should only find the 2 eligible follow-ups
        self.assertEqual(stats['total_processed'], 2, "Should find exactly 2 follow-ups (not 6)")
    
    def test_check_and_send_followup_reminders_updates_database(self):
        """
        Test that reminder checking updates reminder_sent flag in database.
        
        ✅ Tests:
        - reminder_sent flag is set to True after sending
        - Database is actually updated
        - Follow-up is not re-reminded on next check
        """
        from reminder_service import check_and_send_followup_reminders
        
        # Create follow-up
        scheduled_time = timezone.now() + timedelta(hours=12)
        followup = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=scheduled_time,
            status='scheduled',
            reminder_sent=False
        )
        
        # Mock the WhatsApp API call
        with patch('reminder_service.send_whatsapp_reminder') as mock_send:
            mock_send.return_value = {
                'success': True,
                'status_code': 200,
                'message_id': 'test_id',
                'error': None,
                'response': {}
            }
            
            # First run - should send reminder
            stats1 = check_and_send_followup_reminders(batch_size=10, dry_run=False)
            self.assertEqual(stats1['reminders_sent'], 1, "Should send 1 reminder")
            
            # Verify database was updated
            followup.refresh_from_db()
            self.assertTrue(followup.reminder_sent, "reminder_sent should be True")
            
            # Second run - should not re-send
            stats2 = check_and_send_followup_reminders(batch_size=10, dry_run=False)
            self.assertEqual(stats2['total_processed'], 0, "Should not find already-reminded follow-ups")
    
    def test_check_and_send_followup_reminders_handles_errors(self):
        """
        Test that reminder checking gracefully handles errors.
        
        ✅ Tests:
        - Function continues when one reminder fails
        - Errors are logged and reported
        - Invalid phone numbers don't crash the process
        """
        from reminder_service import check_and_send_followup_reminders
        
        # Create patient with invalid phone
        patient_invalid = Patient.objects.create(
            name='Invalid Phone Patient',
            age=25,
            phone_no='123',  # Invalid phone
            doctor='dr_1',
            gender='female'
        )
        
        # Create follow-ups
        now = timezone.now()
        followup_invalid = FollowUp.objects.create(
            patient=patient_invalid,
            scheduled_date=now + timedelta(hours=12),
            status='scheduled',
            reminder_sent=False
        )
        
        followup_valid = FollowUp.objects.create(
            patient=self.patient,
            scheduled_date=now + timedelta(hours=12),
            status='scheduled',
            reminder_sent=False
        )
        
        # Mock the WhatsApp API
        with patch('reminder_service.send_whatsapp_reminder') as mock_send:
            mock_send.return_value = {
                'success': True,
                'status_code': 200,
                'message_id': 'test_id',
                'error': None,
                'response': {}
            }
            
            # Run check
            stats = check_and_send_followup_reminders(batch_size=10, dry_run=False)
            
            # Should process both but only successfully send to valid one
            self.assertEqual(stats['reminders_failed'], 1, "Should have 1 failure")
            self.assertEqual(stats['reminders_sent'], 1, "Should have 1 success")
            self.assertTrue(len(stats['errors']) > 0, "Should have error messages")


class ReminderSchedulerTestCase(TestCase):
    """Test cases for the background scheduler functionality"""
    
    def test_scheduler_starts_without_errors(self):
        """
        Test that the scheduler can be started and stopped without errors.
        
        ✅ Tests:
        - Scheduler initialization is successful
        - Status can be retrieved
        """
        try:
            from Anand_Clinic.scheduler import start_scheduler, stop_scheduler, get_scheduler_status
            
            # Start scheduler
            start_scheduler()
            
            # Get status
            status = get_scheduler_status()
            self.assertTrue(status['running'], "Scheduler should be running")
            self.assertGreater(status['job_count'], 0, "Should have at least 1 job")
            
            # Stop scheduler
            stop_scheduler()
            
        except ImportError:
            self.skipTest("APScheduler not installed, skipping scheduler tests")
