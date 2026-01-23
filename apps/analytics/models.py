from django.db import models
from django.utils import timezone


class DailyStatistic(models.Model):
    """Store daily platform statistics"""
    date = models.DateField(unique=True)
    
    # User statistics
    total_users = models.IntegerField(default=0)
    new_users_today = models.IntegerField(default=0)
    active_users_today = models.IntegerField(default=0)
    
    # Appointment statistics
    total_appointments = models.IntegerField(default=0)
    completed_appointments = models.IntegerField(default=0)
    cancelled_appointments = models.IntegerField(default=0)
    
    # Payment statistics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    number_of_payments = models.IntegerField(default=0)
    
    # Review statistics
    total_reviews = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'daily_statistics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Statistics for {self.date}"