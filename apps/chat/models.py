from django.db import models
from apps.accounts.models import User
from apps.appointments.models import Appointment


class ChatMessage(models.Model):
    """Chat message model for appointment-based conversations"""
    appointment = models.ForeignKey(
        Appointment, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    
    message = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    attachment_type = models.CharField(
        max_length=20,
        choices=(
            ('image', 'Image'),
            ('document', 'Document'),
            ('video', 'Video'),
            ('other', 'Other'),
        ),
        blank=True
    )
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Message status
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['appointment', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"
    
    def mark_as_read(self, user):
        """Mark message as read if user is recipient"""
        from django.utils import timezone
        if not self.is_read and self.sender != user:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class ChatRoom(models.Model):
    """Chat room for general conversations (future feature)"""
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    name = models.CharField(max_length=200, blank=True)
    is_group = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_rooms'
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.name:
            return self.name
        return f"Chat Room {self.id}"
    
    def get_last_message(self):
        """Get the last message in the chat room"""
        return self.room_messages.first()


class RoomMessage(models.Model):
    """Message model for general chat rooms"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='room_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    
    message = models.TextField()
    attachment = models.FileField(upload_to='room_attachments/', blank=True, null=True)
    
    is_read_by = models.ManyToManyField(User, related_name='read_room_messages', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'room_messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"