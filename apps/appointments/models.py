from django.db import models
from django.utils import timezone
from apps.accounts.models import User
from apps.pets.models import Pet


class Appointment(models.Model):
    """Appointment model for scheduling consultations"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    )
    
    CANCELLATION_REASON_CHOICES = (
        ('client_request', 'Client Request'),
        ('vet_unavailable', 'Vet Unavailable'),
        ('emergency', 'Emergency'),
        ('rescheduled', 'Rescheduled'),
        ('other', 'Other'),
    )
    
    client = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='client_appointments',
        limit_choices_to={'user_type': 'client'}
    )
    vet = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='vet_appointments',
        limit_choices_to={'user_type': 'vet'}
    )
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='appointments')
    
    appointment_date = models.DateTimeField()
    duration = models.IntegerField(default=30, help_text="Duration in minutes")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    reason = models.TextField()
    symptoms = models.TextField(blank=True)
    
    # Video meeting details
    meeting_link = models.URLField(blank=True, null=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=50, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True, help_text="Vet's notes")
    prescription = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Cancellation details
    cancelled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='cancelled_appointments'
    )
    cancellation_reason = models.CharField(
        max_length=50, 
        choices=CANCELLATION_REASON_CHOICES,
        blank=True
    )
    cancellation_note = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments'
        ordering = ['-appointment_date']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['vet', 'status']),
            models.Index(fields=['appointment_date']),
        ]
    
    def __str__(self):
        return f"{self.pet.name} - Dr. {self.vet.get_full_name()} on {self.appointment_date}"
    
    def save(self, *args, **kwargs):
        # Generate meeting link if not exists
        if not self.meeting_link and self.status == 'confirmed':
            import uuid
            self.meeting_id = str(uuid.uuid4())[:10].upper()
            self.meeting_password = str(uuid.uuid4())[:6].upper()
            self.meeting_link = f"https://meet.vetconnect.com/{self.meeting_id}"
        
        super().save(*args, **kwargs)
    
    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        return self.appointment_date > timezone.now() and self.status in ['pending', 'confirmed']
    
    @property
    def is_past(self):
        """Check if appointment is in the past"""
        return self.appointment_date < timezone.now()
    
    def cancel(self, cancelled_by, reason, note=''):
        """Cancel the appointment"""
        self.status = 'cancelled'
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.cancellation_note = note
        self.cancelled_at = timezone.now()
        self.save()