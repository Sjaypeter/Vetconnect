from django.db import models
from django.utils import timezone
from apps.accounts.models import User


class Pet(models.Model):
    """Pet model for managing pet profiles"""
    SPECIES_CHOICES = (
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('bird', 'Bird'),
        ('rabbit', 'Rabbit'),
        ('hamster', 'Hamster'),
        ('guinea_pig', 'Guinea Pig'),
        ('reptile', 'Reptile'),
        ('fish', 'Fish'),
        ('other', 'Other'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
    )
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES)
    breed = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    weight = models.DecimalField(max_digits=6, decimal_places=2, help_text="Weight in kg")
    color = models.CharField(max_length=50, blank=True)
    microchip_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    photo = models.ImageField(upload_to='pets/', blank=True, null=True)
    allergies = models.TextField(blank=True)
    medical_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['species']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.species})"
    
    @property
    def age(self):
        """Calculate pet's age in years"""
        today = timezone.now().date()
        age = today.year - self.date_of_birth.year
        if today.month < self.date_of_birth.month or \
           (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
            age -= 1
        return age
    
    @property
    def age_months(self):
        """Calculate pet's age in months"""
        today = timezone.now().date()
        months = (today.year - self.date_of_birth.year) * 12
        months += today.month - self.date_of_birth.month
        return months