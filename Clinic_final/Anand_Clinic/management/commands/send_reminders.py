"""
Django management command to manually trigger reminder checks.

Usage:
    python manage.py send_reminders              # Actually send reminders
    python manage.py send_reminders --dry-run    # Test without sending
    python manage.py send_reminders --demo       # Demo mode (update DB, no API calls)
    python manage.py send_reminders --batch=20  # Process 20 reminders per run
"""

from django.core.management.base import BaseCommand, CommandError
from reminder_service import check_and_send_followup_reminders
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send follow-up appointment reminders to patients via WhatsApp'

    def add_arguments(self, parser):
        """Define command-line arguments for flexibility"""
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Show what reminders would be sent without actually sending them',
        )
        
        parser.add_argument(
            '--demo',
            action='store_true',
            dest='demo_mode',
            help='Demo mode: simulate sending (updates DB, no WhatsApp API calls)',
        )
        
        parser.add_argument(
            '--batch',
            type=int,
            default=10,
            dest='batch_size',
            help='Maximum number of reminders to process in one run (default: 10)',
        )

    def handle(self, *args, **options):
        """Execute the reminder checking and sending logic"""
        
        # Get command-line options
        dry_run = options.get('dry_run', False)
        demo_mode = options.get('demo_mode', False)
        batch_size = options.get('batch_size', 10)
        
        # Validate batch size
        if batch_size < 1:
            raise CommandError('Batch size must be at least 1')
        if batch_size > 100:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Large batch size ({batch_size}) may impact server performance. '
                    'Consider keeping it under 50.'
                )
            )
        
        # Display operation mode
        if demo_mode:
            mode = "🧪 DEMO MODE (Updates DB, No API Calls)"
        elif dry_run:
            mode = "🧪 DRY RUN"
        else:
            mode = "📤 SENDING REMINDERS"
        
        self.stdout.write(self.style.SUCCESS(f"\n{mode}"))
        self.stdout.write(f"Batch size: {batch_size}\n")
        
        try:
            # Call the main reminder function
            stats = check_and_send_followup_reminders(
                batch_size=batch_size, 
                dry_run=dry_run,
                demo_mode=demo_mode
            )
            
            # Format and display results
            self.stdout.write(self.style.SUCCESS("\n✅ Reminder Operation Completed\n"))
            self.stdout.write(f"📊 Summary Statistics:")
            self.stdout.write(f"   • Total follow-ups checked: {stats['total_processed']}")
            self.stdout.write(self.style.SUCCESS(f"   • Reminders sent: {stats['reminders_sent']}"))
            self.stdout.write(self.style.ERROR(f"   • Failed: {stats['reminders_failed']}"))
            self.stdout.write(f"   • Dry run mode: {stats['dry_run']}")
            self.stdout.write(f"   • Demo mode: {stats.get('demo_mode', False)}\n")
            
            # Display any errors that occurred
            if stats['errors']:
                self.stdout.write(self.style.WARNING("\n⚠️  Errors encountered:\n"))
                for i, error in enumerate(stats['errors'], 1):
                    self.stdout.write(f"   {i}. {error}")
                self.stdout.write("")
            
        except Exception as e:
            raise CommandError(f"❌ Failed to execute reminder check: {str(e)}")
