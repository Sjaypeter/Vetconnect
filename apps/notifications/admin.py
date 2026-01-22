from django.contrib import admin
from .models import Notification, EmailLog, SMSLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'priority', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['recipient__username', 'recipient__email', 'subject']
    date_hierarchy = 'sent_at'
    readonly_fields = ['sent_at']


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'phone_number', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['recipient__username', 'phone_number', 'message']
    date_hierarchy = 'sent_at'
    readonly_fields = ['sent_at', 'message_sid']