from rest_framework import serializers
from .models import Notification, EmailLog, SMSLog


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'priority',
            'title', 'message', 'link', 'is_read', 'read_at',
            'email_sent', 'email_sent_at', 'sms_sent', 'sms_sent_at',
            'created_at'
        ]
        read_only_fields = [
            'user', 'is_read', 'read_at', 'email_sent',
            'email_sent_at', 'sms_sent', 'sms_sent_at', 'created_at'
        ]


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for Email Log model"""
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = [
            'id', 'recipient', 'recipient_email', 'subject',
            'body', 'sent_at', 'status', 'error_message'
        ]
        read_only_fields = ['sent_at']


class SMSLogSerializer(serializers.ModelSerializer):
    """Serializer for SMS Log model"""
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    
    class Meta:
        model = SMSLog
        fields = [
            'id', 'recipient', 'recipient_name', 'phone_number',
            'message', 'sent_at', 'status', 'message_sid', 'error_message'
        ]
        read_only_fields = ['sent_at', 'message_sid']