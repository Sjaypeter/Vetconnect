from rest_framework import serializers
from .models import ChatMessage, ChatRoom, RoomMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for Chat Message model"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_type = serializers.CharField(source='sender.user_type', read_only=True)
    sender_profile_picture = serializers.ImageField(source='sender.profile_picture', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'appointment', 'sender', 'sender_name', 'sender_type',
            'sender_profile_picture', 'message', 'attachment', 'attachment_type',
            'is_read', 'read_at', 'is_deleted', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'sender', 'is_read', 'read_at', 'is_deleted',
            'created_at', 'updated_at'
        ]


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat messages"""
    
    class Meta:
        model = ChatMessage
        fields = ['appointment', 'message', 'attachment', 'attachment_type']
    
    def validate_appointment(self, value):
        """Ensure user is part of the appointment"""
        user = self.context['request'].user
        if user not in [value.client, value.vet]:
            raise serializers.ValidationError(
                "You can only send messages to appointments you're part of"
            )
        return value


class RoomMessageSerializer(serializers.ModelSerializer):
    """Serializer for Room Message model"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_profile_picture = serializers.ImageField(source='sender.profile_picture', read_only=True)
    read_by_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RoomMessage
        fields = [
            'id', 'room', 'sender', 'sender_name', 'sender_profile_picture',
            'message', 'attachment', 'read_by_count', 'created_at'
        ]
        read_only_fields = ['sender', 'created_at']
    
    def get_read_by_count(self, obj):
        """Get count of users who read the message"""
        return obj.is_read_by.count()


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for Chat Room model"""
    participants_details = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'is_group', 'participants',
            'participants_details', 'last_message', 'unread_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_participants_details(self, obj):
        """Get basic info of all participants"""
        from apps.accounts.serializers import UserSerializer
        return UserSerializer(obj.participants.all(), many=True).data
    
    def get_last_message(self, obj):
        """Get the last message in the room"""
        last_message = obj.get_last_message()
        if last_message:
            return RoomMessageSerializer(last_message).data
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for current user"""
        request = self.context.get('request')
        if request and request.user:
            return obj.room_messages.exclude(
                is_read_by=request.user
            ).count()
        return 0