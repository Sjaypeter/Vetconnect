import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vetconnect.settings')

# Create Celery app
app = Celery('vetconnect')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()


# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    # Send appointment reminders every hour
    'send-appointment-reminders': {
        'task': 'apps.appointments.tasks.send_appointment_reminders',
        'schedule': crontab(minute=0),  # Every hour
    },
    
    # Send vaccination reminders daily at 9 AM
    'send-vaccination-reminders': {
        'task': 'apps.medical_records.tasks.send_vaccination_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    
    # Check overdue vaccinations daily at 10 AM
    'check-overdue-vaccinations': {
        'task': 'apps.medical_records.tasks.check_overdue_vaccinations',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    
    # Clean up old notifications weekly on Sunday at midnight
    'cleanup-old-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=0, minute=0, day_of_week=0),  # Sunday at midnight
    },
    
    # Check expired payment methods monthly on 1st at 8 AM
    'check-expired-payment-methods': {
        'task': 'apps.payments.tasks.check_expired_payment_methods',
        'schedule': crontab(hour=8, minute=0, day_of_month=1),  # 1st of month
    },
    
    # Send invoice reminders daily at 8 AM
    'send-invoice-reminders': {
        'task': 'apps.payments.tasks.send_invoice_reminders',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    
    # Update appointment statuses every 30 minutes
    'update-appointment-statuses': {
        'task': 'apps.appointments.tasks.update_appointment_statuses',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Generate daily statistics at midnight
    'generate-daily-statistics': {
        'task': 'apps.analytics.tasks.generate_daily_statistics',
        'schedule': crontab(hour=0, minute=5),  # Daily at 12:05 AM
    },
}

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    result_expires=3600,  # 1 hour
)


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')