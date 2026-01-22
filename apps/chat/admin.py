from django.contrib import admin
from .models import ChatMessage, ChatRoom, RoomMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'appointment', 'message', 'is_read', 'is_deleted', 'created_at']
    list_filter = ['is_read', 'is_deleted', 'created_at']
    search_fields = ['sender__username', 'message', 'appointment__pet__name']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_group', 'created_at']
    list_filter = ['is_group', 'created_at']
    search_fields = ['name']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RoomMessage)
class RoomMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'room', 'message', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sender__username', 'message']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']