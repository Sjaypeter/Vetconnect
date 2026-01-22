from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'pet', 'client', 'vet', 'appointment_date', 'duration', 'status', 'created_at']
    list_filter = ['status', 'appointment_date', 'created_at']
    search_fields = [
        'pet__name', 
        'client__username', 
        'client__email',
        'vet__username', 
        'vet__email',
        'reason',
        'meeting_id'
    ]
    readonly_fields = ['meeting_link', 'meeting_id', 'meeting_password', 'created_at', 'updated_at']
    date_hierarchy = 'appointment_date'
    
    fieldsets = (
        ('Appointment Details', {
            'fields': ('client', 'vet', 'pet', 'appointment_date', 'duration', 'status')
        }),
        ('Reason & Symptoms', {
            'fields': ('reason', 'symptoms')
        }),
        ('Video Meeting', {
            'fields': ('meeting_link', 'meeting_id', 'meeting_password'),
            'classes': ('collapse',)
        }),
        ('Medical Notes', {
            'fields': ('notes', 'prescription', 'follow_up_required', 'follow_up_date')
        }),
        ('Cancellation Details', {
            'fields': ('cancelled_by', 'cancellation_reason', 'cancellation_note', 'cancelled_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'{updated} appointments marked as confirmed')
    mark_as_confirmed.short_description = 'Mark selected as confirmed'
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.filter(status='in_progress').update(status='completed')
        self.message_user(request, f'{updated} appointments marked as completed')
    mark_as_completed.short_description = 'Mark selected as completed'
    
    def mark_as_cancelled(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for appointment in queryset.filter(status__in=['pending', 'confirmed']):
            appointment.status = 'cancelled'
            appointment.cancelled_by = request.user
            appointment.cancelled_at = timezone.now()
            appointment.cancellation_reason = 'other'
            appointment.cancellation_note = 'Cancelled by admin'
            appointment.save()
            updated += 1
        self.message_user(request, f'{updated} appointments cancelled')
    mark_as_cancelled.short_description = 'Cancel selected appointments'