from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import MedicalRecord, Vaccination, Prescription
from .serializers import (
    MedicalRecordSerializer, MedicalRecordListSerializer,
    VaccinationSerializer, PrescriptionSerializer
)
from apps.notifications.models import Notification


class MedicalRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for medical records
    
    list: Get all medical records (filtered by user type)
    create: Create new medical record (vet only)
    retrieve: Get specific medical record
    update: Update medical record (vet only)
    partial_update: Partially update medical record (vet only)
    destroy: Delete medical record (admin only)
    """
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['pet', 'vet', 'date', 'follow_up_required']
    search_fields = ['diagnosis', 'treatment', 'prescriptions']
    ordering_fields = ['date', 'created_at']
    
    def get_queryset(self):
        """Filter records based on user type"""
        user = self.request.user
        if user.user_type == 'client':
            # Clients see only their pets' records
            return MedicalRecord.objects.filter(pet__owner=user)
        elif user.user_type == 'vet':
            # Vets see records they created
            return MedicalRecord.objects.filter(vet=user)
        return MedicalRecord.objects.none()
    
    def get_serializer_class(self):
        """Use simplified serializer for list view"""
        if self.action == 'list':
            return MedicalRecordListSerializer
        return MedicalRecordSerializer
    
    def perform_create(self, serializer):
        """Only vets can create medical records"""
        if self.request.user.user_type != 'vet':
            raise PermissionError('Only veterinarians can create medical records')
        
        medical_record = serializer.save(vet=self.request.user)
        
        # Notify pet owner
        Notification.objects.create(
            user=medical_record.pet.owner,
            notification_type='medical_record',
            title='New Medical Record',
            message=f'A new medical record has been added for {medical_record.pet.name}',
            link=f'/api/v1/medical-records/{medical_record.id}/'
        )
    
    @swagger_auto_schema(
        operation_description="Get medical records for a specific pet",
        manual_parameters=[
            openapi.Parameter(
                'pet_id',
                openapi.IN_QUERY,
                description="Pet ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_pet(self, request):
        """Get all medical records for a specific pet"""
        pet_id = request.query_params.get('pet_id')
        if not pet_id:
            return Response(
                {'error': 'pet_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        records = self.get_queryset().filter(pet_id=pet_id)
        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def prescriptions(self, request, pk=None):
        """Get all prescriptions for a medical record"""
        medical_record = self.get_object()
        prescriptions = medical_record.prescription_items.all()
        serializer = PrescriptionSerializer(prescriptions, many=True)
        return Response(serializer.data)


class VaccinationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vaccination records
    
    list: Get all vaccinations
    create: Create new vaccination record
    retrieve: Get specific vaccination
    update: Update vaccination record
    destroy: Delete vaccination record
    upcoming: Get upcoming vaccinations
    overdue: Get overdue vaccinations
    """
    serializer_class = VaccinationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['pet', 'vaccine_name', 'date_administered', 'next_due_date']
    search_fields = ['vaccine_name', 'vaccine_type', 'batch_number']
    ordering_fields = ['date_administered', 'next_due_date']
    
    def get_queryset(self):
        """Filter vaccinations based on user type"""
        user = self.request.user
        if user.user_type == 'client':
            return Vaccination.objects.filter(pet__owner=user)
        elif user.user_type == 'vet':
            return Vaccination.objects.filter(administered_by=user)
        return Vaccination.objects.none()
    
    def perform_create(self, serializer):
        """Set administered_by to current user if vet"""
        if self.request.user.user_type == 'vet':
            serializer.save(administered_by=self.request.user)
        else:
            serializer.save()
    
    @swagger_auto_schema(
        operation_description="Get upcoming vaccinations (due within 30 days)"
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get vaccinations due within 30 days"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        thirty_days = today + timedelta(days=30)
        
        vaccinations = self.get_queryset().filter(
            next_due_date__gte=today,
            next_due_date__lte=thirty_days
        )
        
        serializer = self.get_serializer(vaccinations, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get overdue vaccinations"
    )
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue vaccinations"""
        from django.utils import timezone
        
        today = timezone.now().date()
        vaccinations = self.get_queryset().filter(next_due_date__lt=today)
        
        serializer = self.get_serializer(vaccinations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_pet(self, request):
        """Get all vaccinations for a specific pet"""
        pet_id = request.query_params.get('pet_id')
        if not pet_id:
            return Response(
                {'error': 'pet_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vaccinations = self.get_queryset().filter(pet_id=pet_id)
        serializer = self.get_serializer(vaccinations, many=True)
        return Response(serializer.data)


class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for prescription management
    
    list: Get all prescriptions
    create: Create new prescription (vet only)
    retrieve: Get specific prescription
    update: Update prescription (vet only)
    destroy: Delete prescription
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['medical_record', 'medication_name', 'start_date']
    search_fields = ['medication_name', 'instructions']
    
    def get_queryset(self):
        """Filter prescriptions based on user type"""
        user = self.request.user
        if user.user_type == 'client':
            return Prescription.objects.filter(
                medical_record__pet__owner=user
            )
        elif user.user_type == 'vet':
            return Prescription.objects.filter(
                medical_record__vet=user
            )
        return Prescription.objects.none()
    
    def perform_create(self, serializer):
        """Only vets can create prescriptions"""
        if self.request.user.user_type != 'vet':
            raise PermissionError('Only veterinarians can create prescriptions')
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active prescriptions (not ended)"""
        from django.utils import timezone
        from django.db.models import Q
        
        today = timezone.now().date()
        prescriptions = self.get_queryset().filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        )
        
        serializer = self.get_serializer(prescriptions, many=True)
        return Response(serializer.data)