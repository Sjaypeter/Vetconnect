from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from .models import Notification, EmailLog, SMSLog
from notifications.serializers import NotificationSerializer, EmailLogSerializer, SMSLogSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notifications
    
    list: Get all notifications for current user
    create: Create new notification (admin only)
    retrieve: Get specific notification
    destroy: Delete notification
    mark_read: Mark notification as read
    mark_all_read: Mark all notifications as read
    unread: Get unread notifications
    stats: Get notification statistics
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['notification_type', 'priority', 'is_read']
    http_method_names = ['get', 'post', 'delete', 'patch']  # No PUT
    
    def get_queryset(self):
        """Only show user's own notifications"""
        return Notification.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Set user to current user when creating"""
        serializer.save(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Mark a notification as read",
        responses={200: NotificationSerializer}
    )
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark specific notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Mark all notifications as read",
        responses={200: 'All notifications marked as read'}
    )
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all user's notifications as read"""
        updated = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{updated} notifications marked as read',
            'count': updated
        })
    
    @swagger_auto_schema(
        operation_description="Get unread notifications",
        responses={200: NotificationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get all unread notifications"""
        notifications = self.get_queryset().filter(is_read=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get notification statistics",
        responses={200: openapi.Response('Notification stats')}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics for user"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'unread': queryset.filter(is_read=False).count(),
            'read': queryset.filter(is_read=True).count(),
            'by_type': {},
            'by_priority': {}
        }
        
        # Count by type
        for notif_type, _ in Notification.NOTIFICATION_TYPES:
            count = queryset.filter(notification_type=notif_type).count()
            if count > 0:
                stats['by_type'][notif_type] = count
        
        # Count by priority
        for priority, _ in Notification.PRIORITY_CHOICES:
            count = queryset.filter(priority=priority).count()
            if count > 0:
                stats['by_priority'][priority] = count
        
        return Response(stats)
    
    @swagger_auto_schema(
        operation_description="Delete all read notifications",
        responses={200: 'Read notifications deleted'}
    )
    @action(detail=False, methods=['delete'])
    def delete_read(self, request):
        """Delete all read notifications"""
        deleted_count, _ = self.get_queryset().filter(is_read=True).delete()
        return Response({
            'message': f'{deleted_count} read notifications deleted',
            'count': deleted_count
        })


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for email logs (read-only)
    
    list: Get email logs for current user
    retrieve: Get specific email log
    """
    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'sent_at']
    
    def get_queryset(self):
        """Only show user's own email logs"""
        return EmailLog.objects.filter(recipient=self.request.user)


class SMSLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SMS logs (read-only)
    
    list: Get SMS logs for current user
    retrieve: Get specific SMS log
    """
    serializer_class = SMSLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'sent_at']
    
    def get_queryset(self):
        """Only show user's own SMS logs"""
        return SMSLog.objects.filter(recipient=self.request.user)