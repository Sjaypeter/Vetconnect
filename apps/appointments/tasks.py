from vetconnect.celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from .models import Appointment
from apps.notifications.models import Notification


@shared_task(name='apps.appointments.tasks.send_appointment_reminders')
def send_appointment_reminders():
    """
    Send reminders for appointments 24 hours in advance
    Runs every hour via Celery Beat
    """
    now = timezone.now()
    reminder_time = now + timedelta(hours=24)
    
    # Get appointments in the next 24 hours that haven't been reminded
    appointments = Appointment.objects.filter(
        appointment_date__gte=now,
        appointment_date__lte=reminder_time,
        status__in=['pending', 'confirmed']
    )
    
    sent_count = 0
    
    for appointment in appointments:
        
        # Email to client
        try:
            send_mail(
                subject='Appointment Reminder - VetConnect',
                message=f"""
Hello {appointment.client.get_full_name()},

This is a reminder about your upcoming appointment:

Pet: {appointment.pet.name}
Veterinarian: Dr. {appointment.vet.get_full_name()}
Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}
Duration: {appointment.duration} minutes

Meeting Link: {appointment.meeting_link}
Meeting ID: {appointment.meeting_id}
Password: {appointment.meeting_password}

Reason: {appointment.reason}

Please join the meeting at the scheduled time.

Best regards,
VetConnect Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.client.email],
                fail_silently=True,
            )
            
            # Create notification for client
            Notification.objects.create(
                user=appointment.client,
                notification_type='reminder',
                priority='high',
                title='Appointment Tomorrow',
                message=f'Your appointment with Dr. {appointment.vet.get_full_name()} is in 24 hours',
                link=f'/api/v1/appointments/{appointment.id}/'
            )
            
        except Exception as e:
            print(f"Error sending reminder to client: {e}")
        
        # Email to vet
        try:
            send_mail(
                subject='Appointment Reminder - VetConnect',
                message=f"""
Hello Dr. {appointment.vet.get_full_name()},

This is a reminder about your upcoming appointment:

Client: {appointment.client.get_full_name()}
Pet: {appointment.pet.name} ({appointment.pet.species})
Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}
Duration: {appointment.duration} minutes

Meeting Link: {appointment.meeting_link}

Reason: {appointment.reason}
Symptoms: {appointment.symptoms if appointment.symptoms else 'Not specified'}

Please be prepared to join the meeting at the scheduled time.

Best regards,
VetConnect Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.vet.email],
                fail_silently=True,
            )
            
            # Create notification for vet
            Notification.objects.create(
                user=appointment.vet,
                notification_type='reminder',
                priority='high',
                title='Appointment Tomorrow',
                message=f'Appointment with {appointment.client.get_full_name()} for {appointment.pet.name} in 24 hours',
                link=f'/api/v1/appointments/{appointment.id}/'
            )
            
            sent_count += 1
            
        except Exception as e:
            print(f"Error sending reminder to vet: {e}")
    
    return f"Sent {sent_count} appointment reminders"


@shared_task(name='apps.appointments.tasks.update_appointment_statuses')
def update_appointment_statuses():
    """
    Update appointment statuses based on current time
    - Mark past pending/confirmed appointments as 'no_show'
    - Runs every 30 minutes
    """
    now = timezone.now()
    
    # Mark past appointments as no_show if still pending/confirmed
    no_show_appointments = Appointment.objects.filter(
        appointment_date__lt=now - timedelta(hours=1),  # 1 hour grace period
        status__in=['pending', 'confirmed']
    )
    
    no_show_count = no_show_appointments.count()
    no_show_appointments.update(status='no_show')
    
    return f"Marked {no_show_count} appointments as no-show"


@shared_task
def send_appointment_confirmation(appointment_id):
    """
    Send confirmation email when appointment is confirmed
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        send_mail(
            subject='Appointment Confirmed - VetConnect',
            message=f"""
Hello {appointment.client.get_full_name()},

Your appointment has been confirmed!

Pet: {appointment.pet.name}
Veterinarian: Dr. {appointment.vet.get_full_name()}
Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}

Meeting Details:
Link: {appointment.meeting_link}
Meeting ID: {appointment.meeting_id}
Password: {appointment.meeting_password}

You will receive a reminder 24 hours before your appointment.

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.client.email],
            fail_silently=False,
        )
        
        return f"Confirmation email sent for appointment {appointment_id}"
        
    except Appointment.DoesNotExist:
        return f"Appointment {appointment_id} not found"
    except Exception as e:
        return f"Error sending confirmation: {str(e)}"


@shared_task
def send_appointment_cancellation(appointment_id, cancelled_by_name, reason):
    """
    Send notification when appointment is cancelled
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Determine recipient (the other party)
        if appointment.cancelled_by == appointment.client:
            recipient = appointment.vet
            recipient_name = f"Dr. {recipient.get_full_name()}"
        else:
            recipient = appointment.client
            recipient_name = recipient.get_full_name()
        
        send_mail(
            subject='Appointment Cancelled - VetConnect',
            message=f"""
Hello {recipient_name},

An appointment has been cancelled by {cancelled_by_name}.

Pet: {appointment.pet.name}
Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}
Reason: {appointment.get_cancellation_reason_display()}

{f'Note: {appointment.cancellation_note}' if appointment.cancellation_note else ''}

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )
        
        return f"Cancellation email sent for appointment {appointment_id}"
        
    except Appointment.DoesNotExist:
        return f"Appointment {appointment_id} not found"
    except Exception as e:
        return f"Error sending cancellation: {str(e)}"


@shared_task
def send_appointment_completed_email(appointment_id):
    """
    Send email when appointment is completed
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        send_mail(
            subject='Appointment Completed - VetConnect',
            message=f"""
Hello {appointment.client.get_full_name()},

Your appointment has been completed.

Pet: {appointment.pet.name}
Veterinarian: Dr. {appointment.vet.get_full_name()}
Date: {appointment.appointment_date.strftime('%B %d, %Y')}

{f'Follow-up required: {appointment.follow_up_date}' if appointment.follow_up_required else ''}

You can now leave a review for Dr. {appointment.vet.get_full_name()}.

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.client.email],
            fail_silently=False,
        )
        
        return f"Completion email sent for appointment {appointment_id}"
        
    except Appointment.DoesNotExist:
        return f"Appointment {appointment_id} not found"
    except Exception as e:
        return f"Error sending completion email: {str(e)}"