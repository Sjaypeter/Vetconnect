from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import timedelta
from .models import Appointment
from .serializers import (
    AppointmentSerializer, AppointmentListSerializer,
    AppointmentCancelSerializer
)
from apps.notifications.models import Notification


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for appointment management
    
    list: Get all appointments for current user
    create: Book a new appointment
    retrieve: Get specific appointment details
    update: Update appointment (reschedule)
    partial_update: Partially update appointment
    destroy: Delete appointment
    confirm: Confirm appointment (vet only)
    cancel: Cancel appointment
    complete: Mark appointment as completed (vet only)
    start: Start appointment (change status to in_progress)
    upcoming: Get upcoming appointments
    past: Get past appointments
    today: Get today's appointments
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'vet', 'pet', 'appointment_date']
    search_fields = ['pet__name', 'reason', 'notes']
    ordering_fields = ['appointment_date', 'created_at']
    ordering = ['-appointment_date']
    
    def get_queryset(self):
        """Filter appointments based on user type"""
        user = self.request.user
        
        if user.user_type == 'client':
            return Appointment.objects.filter(client=user)
        elif user.user_type == 'vet':
            return Appointment.objects.filter(vet=user)
        
        return Appointment.objects.none()
    
    def get_serializer_class(self):
        """Use simplified serializer for list view"""
        if self.action == 'list':
            return AppointmentListSerializer
        return AppointmentSerializer
    
    def perform_create(self, serializer):
        """Create appointment and send notifications"""
        if self.request.user.user_type != 'client':
            raise PermissionError('Only clients can book appointments')
        
        appointment = serializer.save(client=self.request.user)
        
        # Notify vet about new appointment request
        Notification.objects.create(
            user=appointment.vet,
            notification_type='appointment',
            priority='high',
            title='New Appointment Request',
            message=f'{appointment.client.get_full_name()} has requested an appointment for {appointment.pet.name}',
            link=f'/api/v1/appointments/{appointment.id}/'
        )
    
    def perform_update(self, serializer):
        """Update appointment and notify parties"""
        appointment = self.get_object()
        old_date = appointment.appointment_date
        updated_appointment = serializer.save()
        
        # If appointment date changed, notify both parties
        if old_date != updated_appointment.appointment_date:
            # Notify vet
            Notification.objects.create(
                user=updated_appointment.vet,
                notification_type='appointment',
                priority='medium',
                title='Appointment Rescheduled',
                message=f'Appointment with {updated_appointment.client.get_full_name()} has been rescheduled',
                link=f'/api/v1/appointments/{updated_appointment.id}/'
            )
            
            # Notify client
            Notification.objects.create(
                user=updated_appointment.client,
                notification_type='appointment',
                priority='medium',
                title='Appointment Rescheduled',
                message=f'Your appointment with Dr. {updated_appointment.vet.get_full_name()} has been rescheduled',
                link=f'/api/v1/appointments/{updated_appointment.id}/'
            )
    
    @swagger_auto_schema(
        operation_description="Confirm appointment (vet only)",
        responses={200: AppointmentSerializer}
    )
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm appointment - vet only"""
        appointment = self.get_object()
        
        if request.user != appointment.vet:
            return Response(
                {'error': 'Only the assigned vet can confirm appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status != 'pending':
            return Response(
                {'error': f'Cannot confirm appointment with status: {appointment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'confirmed'
        appointment.save()
        
        # Notify client
        Notification.objects.create(
            user=appointment.client,
            notification_type='appointment',
            priority='high',
            title='Appointment Confirmed',
            message=f'Your appointment with Dr. {appointment.vet.get_full_name()} has been confirmed',
            link=f'/api/v1/appointments/{appointment.id}/'
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Cancel appointment",
        request_body=AppointmentCancelSerializer,
        responses={200: AppointmentSerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel appointment"""
        appointment = self.get_object()
        serializer = AppointmentCancelSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Only client or assigned vet can cancel
        if request.user not in [appointment.client, appointment.vet]:
            return Response(
                {'error': 'You do not have permission to cancel this appointment'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status in ['completed', 'cancelled']:
            return Response(
                {'error': f'Cannot cancel appointment with status: {appointment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel appointment
        appointment.cancel(
            cancelled_by=request.user,
            reason=serializer.validated_data['reason'],
            note=serializer.validated_data.get('note', '')
        )
        
        # Notify the other party
        recipient = appointment.vet if request.user == appointment.client else appointment.client
        Notification.objects.create(
            user=recipient,
            notification_type='appointment',
            priority='high',
            title='Appointment Cancelled',
            message=f'An appointment has been cancelled by {request.user.get_full_name()}',
            link=f'/api/v1/appointments/{appointment.id}/'
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Mark appointment as completed (vet only)",
        responses={200: AppointmentSerializer}
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment as completed - vet only"""
        appointment = self.get_object()
        
        if request.user != appointment.vet:
            return Response(
                {'error': 'Only the assigned vet can complete appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status != 'in_progress':
            return Response(
                {'error': 'Only in-progress appointments can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'completed'
        appointment.save()
        
        # Update vet's total consultations
        if hasattr(appointment.vet, 'vet_profile'):
            vet_profile = appointment.vet.vet_profile
            vet_profile.total_consultations += 1
            vet_profile.save()
        
        # Notify client
        Notification.objects.create(
            user=appointment.client,
            notification_type='appointment',
            priority='medium',
            title='Appointment Completed',
            message=f'Your appointment with Dr. {appointment.vet.get_full_name()} has been completed',
            link=f'/api/v1/appointments/{appointment.id}/'
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Start appointment (change to in_progress)",
        responses={200: AppointmentSerializer}
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start appointment - change status to in_progress"""
        appointment = self.get_object()
        
        if request.user != appointment.vet:
            return Response(
                {'error': 'Only the assigned vet can start appointments'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if appointment.status != 'confirmed':
            return Response(
                {'error': 'Only confirmed appointments can be started'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'in_progress'
        appointment.save()
        
        # Notify client
        Notification.objects.create(
            user=appointment.client,
            notification_type='appointment',
            priority='high',
            title='Appointment Started',
            message=f'Dr. {appointment.vet.get_full_name()} has started your appointment',
            link=f'/api/v1/appointments/{appointment.id}/'
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get upcoming appointments",
        responses={200: AppointmentListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get all upcoming appointments"""
        now = timezone.now()
        appointments = self.get_queryset().filter(
            appointment_date__gte=now,
            status__in=['pending', 'confirmed']
        ).order_by('appointment_date')
        
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get past appointments",
        responses={200: AppointmentListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def past(self, request):
        """Get all past appointments"""
        now = timezone.now()
        appointments = self.get_queryset().filter(
            appointment_date__lt=now
        ).order_by('-appointment_date')
        
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get today's appointments",
        responses={200: AppointmentListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get all appointments for today"""
        today = timezone.now().date()
        appointments = self.get_queryset().filter(
            appointment_date__date=today
        ).order_by('appointment_date')
        
        serializer = AppointmentListSerializer(appointments, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get appointment statistics",
        responses={200: 'Appointment statistics'}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get appointment statistics for current user"""
        queryset = self.get_queryset()
        user = request.user
        
        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(status='pending').count(),
            'confirmed': queryset.filter(status='confirmed').count(),
            'in_progress': queryset.filter(status='in_progress').count(),
            'completed': queryset.filter(status='completed').count(),
            'cancelled': queryset.filter(status='cancelled').count(),
        }
        
        # Add upcoming count
        now = timezone.now()
        stats['upcoming'] = queryset.filter(
            appointment_date__gte=now,
            status__in=['pending', 'confirmed']
        ).count()
        
        # Add today's count
        today = timezone.now().date()
        stats['today'] = queryset.filter(
            appointment_date__date=today
        ).count()
        
        # Add this week's count
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        stats['this_week'] = queryset.filter(
            appointment_date__date__gte=week_start,
            appointment_date__date__lte=week_end
        ).count()
        
        return Response(stats)