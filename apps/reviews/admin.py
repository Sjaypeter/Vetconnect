from django.contrib import admin
from .models import Review, ReviewHelpful


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['vet', 'client', 'rating', 'would_recommend', 'is_approved', 'is_flagged', 'created_at']
    list_filter = ['rating', 'would_recommend', 'is_approved', 'is_flagged', 'created_at']
    search_fields = ['vet__username', 'client__username', 'comment']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vet', 'client', 'appointment')
        }),
        ('Ratings', {
            'fields': ('rating', 'communication_rating', 'professionalism_rating', 'care_quality_rating', 'would_recommend')
        }),
        ('Review Content', {
            'fields': ('comment',)
        }),
        ('Moderation', {
            'fields': ('is_approved', 'is_flagged', 'flag_reason')
        }),
        ('Vet Response', {
            'fields': ('vet_response', 'vet_response_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['review__id', 'user__username']
    date_hierarchy = 'created_at'