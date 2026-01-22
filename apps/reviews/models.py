from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.accounts.models import User
from apps.appointments.models import Appointment


class Review(models.Model):
    """Review and rating model for veterinarians"""
    vet = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        limit_choices_to={'user_type': 'vet'}
    )
    client = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='given_reviews',
        limit_choices_to={'user_type': 'client'}
    )
    appointment = models.OneToOneField(
        Appointment, 
        on_delete=models.CASCADE,
        related_name='review'
    )
    
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(blank=True)
    
    # Detailed ratings (optional)
    communication_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    professionalism_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    care_quality_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Recommendations
    would_recommend = models.BooleanField(default=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.TextField(blank=True)
    
    # Response from vet
    vet_response = models.TextField(blank=True)
    vet_response_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        unique_together = ['vet', 'client', 'appointment']
        indexes = [
            models.Index(fields=['vet', '-created_at']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.client.username} rated Dr. {self.vet.get_full_name()} - {self.rating}/5"
    
    def save(self, *args, **kwargs):
        """Update vet's average rating after saving review"""
        super().save(*args, **kwargs)
        
        # Update vet profile rating
        if hasattr(self.vet, 'vet_profile'):
            self.vet.vet_profile.update_rating()


class ReviewHelpful(models.Model):
    """Track users who found a review helpful"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_helpful'
        unique_together = ['review', 'user']
    
    def __str__(self):
        return f"{self.user.username} found review #{self.review.id} helpful"