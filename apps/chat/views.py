from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from .models import ChatMessage, ChatRoom, RoomMessage
from .serializers import (
    ChatMessageSerializer, ChatMessageCreateSerializer,
    ChatRoomSerializer, RoomMessageSerializer
)
from apps.notifications.models import Notification


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat messages (appointment-based)
    
    list: Get all messages for user's appointments
    create: Send a new message
    retrieve: Get specific message
    destroy: Delete message (soft delete)
    by_appointment: Get messages for specific appointment
    mark_read: Mark message as read
    unread_count: Get unread message count
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['appointment', 'sender', 'is_read']
    
    def get_queryset(self):
        """Get messages for user's appointments"""
        user = self.request.user
        
        # Get all appointments where user is either client or vet
        from apps.appointments.models import Appointment
        user_appointments = Appointment.objects.filter(
            Q(client=user) | Q(vet=user)
        )
        
        return ChatMessage.objects.filter(
            appointment__in=user_appointments,
            is_deleted=False
        )
    
    def get_serializer_class(self):
        """Use different serializer for create action"""
        if self.action == 'create':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer
    
    def perform_create(self, serializer):
        """Create message and send notification"""
        message = serializer.save(sender=self.request.user)
        
        # Determine recipient (other party in appointment)
        appointment = message.appointment
        recipient = appointment.vet if self.request.user == appointment.client else appointment.client
        
        # Create notification
        Notification.objects.create(
            user=recipient,
            notification_type='message',
            title='New Message',
            message=f'{self.request.user.get_full_name()} sent you a message',
            link=f'/api/v1/appointments/{appointment.id}/',
            priority='medium'
        )
    
    def perform_destroy(self, instance):
        """Soft delete message"""
        from django.utils import timezone
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
    
    @swagger_auto_schema(
        operation_description="Get messages for a specific appointment",
        manual_parameters=[
            openapi.Parameter(
                'appointment_id',
                openapi.IN_QUERY,
                description="Appointment ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_appointment(self, request):
        """Get all messages for a specific appointment"""
        appointment_id = request.query_params.get('appointment_id')
        
        if not appointment_id:
            return Response(
                {'error': 'appointment_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = self.get_queryset().filter(appointment_id=appointment_id)
        
        # Mark messages as read if user is recipient
        for message in messages:
            message.mark_as_read(request.user)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark specific message as read"""
        message = self.get_object()
        message.mark_as_read(request.user)
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get unread message count",
        responses={200: openapi.Response('Unread count')}
    )
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread messages"""
        count = self.get_queryset().filter(
            is_read=False
        ).exclude(
            sender=request.user
        ).count()
        
        return Response({'unread_count': count})


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat rooms (future feature)
    
    list: Get all chat rooms user is part of
    create: Create new chat room
    retrieve: Get specific chat room
    update: Update chat room
    destroy: Delete chat room
    messages: Get messages in room
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get chat rooms user is part of"""
        return ChatRoom.objects.filter(participants=self.request.user)
    
    def perform_create(self, serializer):
        """Create chat room and add creator as participant"""
        chat_room = serializer.save()
        chat_room.participants.add(self.request.user)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in a chat room"""
        chat_room = self.get_object()
        messages = chat_room.room_messages.all()
        serializer = RoomMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add participant to chat room"""
        chat_room = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import User
            user = User.objects.get(id=user_id)
            chat_room.participants.add(user)
            return Response({'message': f'{user.get_full_name()} added to chat room'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Remove participant from chat room"""
        chat_room = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.accounts.models import User
            user = User.objects.get(id=user_id)
            chat_room.participants.remove(user)
            return Response({'message': f'{user.get_full_name()} removed from chat room'})
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class RoomMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for room messages
    
    list: Get messages from user's rooms
    create: Send message to room
    retrieve: Get specific message
    """
    serializer_class = RoomMessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['room']
    
    def get_queryset(self):
        """Get messages from rooms user is part of"""
        user_rooms = ChatRoom.objects.filter(participants=self.request.user)
        return RoomMessage.objects.filter(room__in=user_rooms)
    
    def perform_create(self, serializer):
        """Create message and mark as read by sender"""
        message = serializer.save(sender=self.request.user)
        message.is_read_by.add(self.request.user)