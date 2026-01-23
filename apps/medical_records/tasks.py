# apps/medical_records/tasks.py
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta, date
from .models import Vaccination, MedicalRecord
from apps.notifications.models import Notification
from apps.pets.models import Pet
from .models import MedicalRecord


@shared_task(name='apps.medical_records.tasks.send_vaccination_reminders')
def send_vaccination_reminders():
    """
    Send reminders for vaccinations due within 7 days
    Runs daily at 9 AM
    """
    today = timezone.now().date()
    reminder_date = today + timedelta(days=7)
    
    # Get vaccinations due within the next 7 days
    upcoming_vaccinations = Vaccination.objects.filter(
        next_due_date__gte=today,
        next_due_date__lte=reminder_date,
        reminder_sent=False
    )
    
    sent_count = 0
    
    for vaccination in upcoming_vaccinations:
        pet = vaccination.pet
        owner = pet.owner
        
        try:
            # Send email
            send_mail(
                subject=f'Vaccination Reminder for {pet.name} - VetConnect',
                message=f"""
Hello {owner.get_full_name()},

This is a reminder that {pet.name} is due for a vaccination:

Vaccine: {vaccination.vaccine_name}
Due Date: {vaccination.next_due_date.strftime('%B %d, %Y')}
Pet: {pet.name} ({pet.species})

{f'Last administered: {vaccination.date_administered.strftime("%B %d, %Y")}' if vaccination.date_administered else ''}

Please schedule an appointment with your veterinarian to ensure your pet stays protected.

Best regards,
VetConnect Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.email],
                fail_silently=True,
            )
            
            # Create notification
            Notification.objects.create(
                user=owner,
                notification_type='reminder',
                priority='medium',
                title='Vaccination Due Soon',
                message=f'{pet.name} is due for {vaccination.vaccine_name} vaccination on {vaccination.next_due_date}',
                link=f'/api/v1/pets/{pet.id}/'
            )
            
            # Mark reminder as sent
            vaccination.reminder_sent = True
            vaccination.save()
            
            sent_count += 1
            
        except Exception as e:
            print(f"Error sending vaccination reminder: {e}")
    
    return f"Sent {sent_count} vaccination reminders"


@shared_task(name='apps.medical_records.tasks.check_overdue_vaccinations')
def check_overdue_vaccinations():
    """
    Check for overdue vaccinations and notify owners
    Runs daily at 10 AM
    """
    today = timezone.now().date()
    
    # Get overdue vaccinations
    overdue_vaccinations = Vaccination.objects.filter(
        next_due_date__lt=today,
        reminder_sent=True  # Only those that were reminded but still overdue
    )
    
    notified_count = 0
    
    for vaccination in overdue_vaccinations:
        pet = vaccination.pet
        owner = pet.owner
        days_overdue = (today - vaccination.next_due_date).days
        
        # Only send if overdue by more than 7 days and not sent in last 7 days
        if days_overdue % 7 == 0:  # Send weekly reminders
            try:
                # Send email
                send_mail(
                    subject=f'URGENT: Overdue Vaccination for {pet.name} - VetConnect',
                    message=f"""
Hello {owner.get_full_name()},

IMPORTANT: {pet.name}'s vaccination is now overdue.

Vaccine: {vaccination.vaccine_name}
Was Due: {vaccination.next_due_date.strftime('%B %d, %Y')}
Days Overdue: {days_overdue}

It is important to keep your pet's vaccinations up to date to protect their health.

Please schedule an appointment as soon as possible.

Best regards,
VetConnect Team
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[owner.email],
                    fail_silently=True,
                )
                
                # Create high priority notification
                Notification.objects.create(
                    user=owner,
                    notification_type='reminder',
                    priority='high',
                    title='OVERDUE: Vaccination Required',
                    message=f'{pet.name}\'s {vaccination.vaccine_name} vaccination is {days_overdue} days overdue',
                    link=f'/api/v1/pets/{pet.id}/'
                )
                
                notified_count += 1
                
            except Exception as e:
                print(f"Error sending overdue notification: {e}")
    
    return f"Sent {notified_count} overdue vaccination notifications"


@shared_task
def send_medical_record_notification(medical_record_id):
    """
    Send notification when a new medical record is created
    """
    try:
        from .models import MedicalRecord
        medical_record = MedicalRecord.objects.get(id=medical_record_id)
        
        pet = medical_record.pet
        owner = pet.owner
        
        send_mail(
            subject=f'New Medical Record for {pet.name} - VetConnect',
            message=f"""
Hello {owner.get_full_name()},

A new medical record has been added for {pet.name}.

Date: {medical_record.date.strftime('%B %d, %Y')}
Veterinarian: Dr. {medical_record.vet.get_full_name()}
Diagnosis: {medical_record.diagnosis}

{f'Follow-up Required: {medical_record.follow_up_date}' if medical_record.follow_up_required else ''}

You can view the complete medical record in your VetConnect account.

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=False,
        )
        
        return f"Medical record notification sent for record {medical_record_id}"
        
    except MedicalRecord.DoesNotExist:
        return f"Medical record {medical_record_id} not found"
    except Exception as e:
        return f"Error sending medical record notification: {str(e)}"


@shared_task
def send_follow_up_reminder(medical_record_id):
    """
    Send reminder for follow-up appointments
    """
    try:
        medical_record = MedicalRecord.objects.get(id=medical_record_id)
        
        if not medical_record.follow_up_required:
            return "Follow-up not required"
        
        pet = medical_record.pet
        owner = pet.owner
        
        send_mail(
            subject=f'Follow-up Reminder for {pet.name} - VetConnect',
            message=f"""
Hello {owner.get_full_name()},

This is a reminder about a follow-up appointment for {pet.name}.

Original Visit: {medical_record.date.strftime('%B %d, %Y')}
Follow-up Due: {medical_record.follow_up_date}
Veterinarian: Dr. {medical_record.vet.get_full_name()}

{f'Instructions: {medical_record.follow_up_instructions}' if medical_record.follow_up_instructions else ''}

Please schedule your follow-up appointment.

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=False,
        )
        
        # Create notification
        Notification.objects.create(
            user=owner,
            notification_type='reminder',
            priority='medium',
            title='Follow-up Appointment Due',
            message=f'Follow-up required for {pet.name} on {medical_record.follow_up_date}',
            link=f'/api/v1/medical-records/{medical_record.id}/'
        )
        
        return f"Follow-up reminder sent for medical record {medical_record_id}"
        
    except MedicalRecord.DoesNotExist:
        return f"Medical record {medical_record_id} not found"
    except Exception as e:
        return f"Error sending follow-up reminder: {str(e)}"


@shared_task
def generate_pet_health_report(pet_id):
    """
    Generate comprehensive health report for a pet
    """
    try:
        pet = Pet.objects.get(id=pet_id)
        owner = pet.owner
        
        # Get medical records
        medical_records = MedicalRecord.objects.filter(pet=pet).order_by('-date')[:5]
        vaccinations = Vaccination.objects.filter(pet=pet).order_by('-date_administered')[:5]
        
        # Build report
        report = f"""
Health Report for {pet.name}
Generated: {timezone.now().strftime('%B %d, %Y')}

Pet Information:
- Species: {pet.species}
- Breed: {pet.breed}
- Age: {pet.age} years
- Weight: {pet.weight} kg

Recent Medical Records:
"""
        for record in medical_records:
            report += f"\n- {record.date.strftime('%Y-%m-%d')}: {record.diagnosis}"
        
        report += "\n\nVaccination History:"
        for vaccination in vaccinations:
            report += f"\n- {vaccination.vaccine_name}: {vaccination.date_administered.strftime('%Y-%m-%d')}"
        
        # Send email with report
        send_mail(
            subject=f'Health Report for {pet.name} - VetConnect',
            message=report,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=False,
        )
        
        return f"Health report generated for pet {pet_id}"
        
    except Exception as e:
        return f"Error generating health report: {str(e)}"