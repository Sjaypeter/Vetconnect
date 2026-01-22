from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, VetProfile, ClientProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'user_type', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['user_type', 'is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone', 'profile_picture')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('user_type', 'phone', 'email', 'first_name', 'last_name')
        }),
    )


@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'license_number', 'years_of_experience', 'is_verified', 'rating', 'total_consultations']
    list_filter = ['is_verified', 'specialization', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'specialization', 'license_number']
    readonly_fields = ['rating', 'total_consultations', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Veterinarian Information', {
            'fields': ('user', 'specialization', 'license_number', 'years_of_experience', 'bio')
        }),
        ('Professional Details', {
            'fields': ('consultation_fee', 'available_days', 'available_hours')
        }),
        ('Verification & Stats', {
            'fields': ('is_verified', 'rating', 'total_consultations')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'emergency_contact', 'preferred_language', 'created_at']
    list_filter = ['preferred_language', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'address']
    readonly_fields = ['created_at', 'updated_at']
