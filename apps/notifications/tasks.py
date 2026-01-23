from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
from datetime import timedelta
from .models import Notification, EmailLog, SMSLog


@shared_task(name='apps.notifications.tasks.cleanup_old_notifications')
def cleanup_old_notifications():
    """
    Delete read notifications older than 30 days
    Runs weekly on Sunday at midnight
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Delete old read notifications
    deleted_count = Notification.objects.filter(
        is_read=True,
        created_at__lt=thirty_days_ago
    ).delete()[0]
    
    return f"Deleted {deleted_count} old notifications"


@shared_task
def send_email_notification(notification_id):
    """
    Send email for a notification
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user
        
        # Create email log
        email_log = EmailLog.objects.create(
            recipient=user,
            subject=notification.title,
            body=notification.message,
            status='pending'
        )
        
        try:
            send_mail(
                subject=notification.title,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Update notification
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save()
            
            # Update email log
            email_log.status = 'sent'
            email_log.save()
            
            return f"Email sent for notification {notification_id}"
            
        except Exception as e:
            email_log.status = 'failed'
            email_log.error_message = str(e)
            email_log.save()
            raise
            
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Error sending email: {str(e)}"


@shared_task
def send_sms_notification(notification_id):
    """
    Send SMS for a notification using Twilio
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.user
        
        if not user.phone:
            return f"User {user.username} has no phone number"
        
        # Create SMS log
        sms_log = SMSLog.objects.create(
            recipient=user,
            phone_number=user.phone,
            message=notification.message,
            status='pending'
        )
        
        try:
            from twilio.rest import Client
            
            # Initialize Twilio client
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
            twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
            
            if not all([account_sid, auth_token, twilio_phone]):
                raise Exception("Twilio credentials not configured")
            
            client = Client(account_sid, auth_token)
            
            # Send SMS
            message = client.messages.create(
                body=notification.message,
                from_=twilio_phone,
                to=user.phone
            )
            
            # Update notification
            notification.sms_sent = True
            notification.sms_sent_at = timezone.now()
            notification.save()
            
            # Update SMS log
            sms_log.status = 'sent'
            sms_log.message_sid = message.sid
            sms_log.save()
            
            return f"SMS sent for notification {notification_id}"
            
        except Exception as e:
            sms_log.status = 'failed'
            sms_log.error_message = str(e)
            sms_log.save()
            raise
            
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Error sending SMS: {str(e)}"


@shared_task
def send_bulk_email(user_ids, subject, message):
    """
    Send bulk email to multiple users
    """
    from apps.accounts.models import User
    
    users = User.objects.filter(id__in=user_ids)
    
    # Prepare messages
    messages = [
        (
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        for user in users if user.email
    ]
    
    # Send mass email
    try:
        sent_count = send_mass_mail(messages, fail_silently=False)
        
        # Create email logs
        for user in users:
            EmailLog.objects.create(
                recipient=user,
                subject=subject,
                body=message,
                status='sent'
            )
        
        return f"Sent {sent_count} bulk emails"
        
    except Exception as e:
        return f"Error sending bulk email: {str(e)}"


@shared_task
def send_digest_email(user_id):
    """
    Send daily digest of unread notifications
    """
    try:
        from apps.accounts.models import User
        user = User.objects.get(id=user_id)
        
        # Get unread notifications from last 24 hours
        yesterday = timezone.now() - timedelta(days=1)
        notifications = Notification.objects.filter(
            user=user,
            is_read=False,
            created_at__gte=yesterday
        ).order_by('-created_at')
        
        if not notifications.exists():
            return f"No unread notifications for user {user_id}"
        
        # Build digest message
        message = f"""
Hello {user.get_full_name()},

Here's your daily digest of unread notifications:

"""
        for notification in notifications:
            message += f"""
{notification.created_at.strftime('%I:%M %p')} - {notification.title}
{notification.message}
---
"""
        
        message += """
Visit VetConnect to view all your notifications.

Best regards,
VetConnect Team
        """
        
        send_mail(
            subject='Your Daily VetConnect Digest',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return f"Digest email sent to user {user_id}"
        
    except Exception as e:
        return f"Error sending digest: {str(e)}"


@shared_task
def process_notification_queue():
    """
    Process pending notifications and send via email/SMS
    """
    # Get high priority notifications that haven't been sent
    high_priority = Notification.objects.filter(
        priority='high',
        email_sent=False,
        created_at__gte=timezone.now() - timedelta(hours=1)
    )[:50]  # Process in batches
    
    email_count = 0
    sms_count = 0
    
    for notification in high_priority:
        # Send email
        send_email_notification.delay(notification.id)
        email_count += 1
        
        # Send SMS for urgent notifications
        if notification.priority == 'urgent':
            send_sms_notification.delay(notification.id)
            sms_count += 1
    
    return f"Queued {email_count} emails and {sms_count} SMS messages"