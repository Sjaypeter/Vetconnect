from django.db import models
from django.utils import timezone
from apps.accounts.models import User
from apps.pets.models import Pet
from apps.appointments.models import Appointment


class MedicalRecord(models.Model):
    """Medical record for pet health history"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='medical_records')
    vet = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_records')
    appointment = models.ForeignKey(
        Appointment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='medical_records'
    )
    
    date = models.DateTimeField(default=timezone.now)
    diagnosis = models.TextField()
    treatment = models.TextField()
    prescriptions = models.TextField(blank=True)
    test_results = models.TextField(blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_instructions = models.TextField(blank=True)
    
    # Attachments
    attachments = models.FileField(upload_to='medical_records/', blank=True, null=True)
    
    # Vitals
    temperature = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True,
        help_text="Temperature in Celsius"
    )
    heart_rate = models.IntegerField(null=True, blank=True, help_text="Beats per minute")
    respiratory_rate = models.IntegerField(null=True, blank=True, help_text="Breaths per minute")
    weight = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Weight in kg"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_records'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['pet', '-date']),
            models.Index(fields=['vet', '-date']),
        ]
    
    def __str__(self):
        return f"{self.pet.name} - {self.date.strftime('%Y-%m-%d')}"


class Vaccination(models.Model):
    """Vaccination record for pets"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine_name = models.CharField(max_length=100)
    vaccine_type = models.CharField(max_length=50, blank=True)
    
    date_administered = models.DateField()
    next_due_date = models.DateField()
    
    administered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='administered_vaccinations'
    )
    
    batch_number = models.CharField(max_length=50, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    
    # Reminder
    reminder_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vaccinations'
        ordering = ['-date_administered']
        indexes = [
            models.Index(fields=['pet', '-date_administered']),
            models.Index(fields=['next_due_date']),
        ]
    
    def __str__(self):
        return f"{self.pet.name} - {self.vaccine_name}"
    
    @property
    def is_due_soon(self):
        """Check if vaccination is due within 30 days"""
        today = timezone.now().date()
        days_until_due = (self.next_due_date - today).days
        return 0 <= days_until_due <= 30
    
    @property
    def is_overdue(self):
        """Check if vaccination is overdue"""
        return self.next_due_date < timezone.now().date()


class Prescription(models.Model):
    """Prescription model for medications"""
    medical_record = models.ForeignKey(
        MedicalRecord, 
        on_delete=models.CASCADE, 
        related_name='prescription_items'
    )
    
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100, help_text="e.g., Twice daily")
    duration = models.CharField(max_length=100, help_text="e.g., 7 days")
    quantity = models.IntegerField(help_text="Number of units")
    instructions = models.TextField()
    
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.medication_name} - {self.dosage}"