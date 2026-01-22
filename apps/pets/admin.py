from django.contrib import admin
from .models import Pet


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ['name', 'species', 'breed', 'owner', 'age', 'gender', 'is_active', 'created_at']
    list_filter = ['species', 'gender', 'is_active', 'created_at']
    search_fields = ['name', 'breed', 'owner__username', 'owner__email', 'microchip_number']
    readonly_fields = ['age', 'age_months', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'species', 'breed', 'photo')
        }),
        ('Physical Details', {
            'fields': ('date_of_birth', 'age', 'age_months', 'gender', 'weight', 'color')
        }),
        ('Identification', {
            'fields': ('microchip_number',)
        }),
        ('Medical Information', {
            'fields': ('allergies', 'medical_notes')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
