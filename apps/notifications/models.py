from django.db import models
from apps.accounts.models import User


class Notification(models.Model):
    """Notification model for in-app notifications"""
    NOTIFICATION_TYPES = (
        ('appointment', 'Appointment'),
        ('message', 'Message'),
        ('reminder', 'Reminder'),
        ('medical_record', 'Medical Record'),
        ('review', 'Review'),
        ('system', 'System'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True)
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Email notification
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # SMS notification
    sms_sent = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class EmailLog(models.Model):
    """Log for tracking sent emails"""
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_logs')
    subject = models.CharField(max_length=200)
    body = models.TextField()
    
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('pending', 'Pending'),
        ),
        default='pending'
    )
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'email_logs'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.recipient.email} - {self.subject}"


class SMSLog(models.Model):
    """Log for tracking sent SMS messages"""
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sms_logs')
    phone_number = models.CharField(max_length=15)
    message = models.TextField()
    
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('pending', 'Pending'),
        ),
        default='pending'
    )
    message_sid = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'sms_logs'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.phone_number} - {self.message[:50]}"