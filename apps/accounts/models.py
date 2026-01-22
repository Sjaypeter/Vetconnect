from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """Custom User model with role-based access"""
    USER_TYPE_CHOICES = (
        ('client', 'Client'),
        ('vet', 'Veterinarian'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.user_type})"


class VetProfile(models.Model):
    """Extended profile for veterinarians"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vet_profile')
    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.IntegerField(default=0)
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    available_days = models.JSONField(default=list)  # ["Monday", "Tuesday", ...]
    available_hours = models.JSONField(default=dict)  # {"start": "09:00", "end": "17:00"}
    is_verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_consultations = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vet_profiles'
        ordering = ['-rating', '-years_of_experience']
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"
    
    def update_rating(self):
        """Update average rating from reviews"""
        from apps.reviews.models import Review
        from django.db.models import Avg
        avg_rating = Review.objects.filter(vet=self.user).aggregate(Avg('rating'))['rating__avg']
        self.rating = avg_rating or 0
        self.save()


class ClientProfile(models.Model):
    """Extended profile for clients/pet owners"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    preferred_language = models.CharField(max_length=20, default='en')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client_profiles'
    
    def __str__(self):
        return self.user.get_full_name()