from django.apps import AppConfig
import os

class AnandClinicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Anand_Clinic"

    def ready(self):
        """
        Called when Django application is ready.
        This is where we initialize background tasks and signal handlers.
        """
        # Only run in the actual server process, not the file watcher
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        # Import signal handlers for model events
        import Anand_Clinic.signal
        
        # Initialize the WhatsApp reminder scheduler
        # This starts a background thread to check for reminders every 15 minutes
        try:
            from async_tasks import start_scheduler
            start_scheduler()
        except Exception as e:
            # Log warning but don't crash Django startup if scheduler fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ Failed to start scheduler: {e}")

class PatientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Anand_Clinic'
