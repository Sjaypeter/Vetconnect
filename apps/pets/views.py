from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Pet
from .serializers import PetSerializer, PetListSerializer


class PetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for pet management
    
    list: Get all pets owned by current user
    create: Register a new pet
    retrieve: Get specific pet details
    update: Update pet information
    partial_update: Partially update pet information
    destroy: Delete a pet (soft delete by setting is_active=False)
    medical_history: Get complete medical history for a pet
    vaccinations: Get vaccination records for a pet
    appointments: Get appointment history for a pet
    """
    serializer_class = PetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['species', 'gender', 'is_active']
    search_fields = ['name', 'breed', 'microchip_number']
    ordering_fields = ['name', 'date_of_birth', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Only show pets owned by current user"""
        user = self.request.user
        
        if user.user_type == 'client':
            return Pet.objects.filter(owner=user)
        elif user.user_type == 'vet':
            # Vets can see pets they have appointments with
            from apps.appointments.models import Appointment
            pet_ids = Appointment.objects.filter(
                vet=user
            ).values_list('pet_id', flat=True).distinct()
            return Pet.objects.filter(id__in=pet_ids)
        
        return Pet.objects.none()
    
    def get_serializer_class(self):
        """Use simplified serializer for list view"""
        if self.action == 'list':
            return PetListSerializer
        return PetSerializer
    
    def perform_create(self, serializer):
        """Set owner to current user when creating pet"""
        if self.request.user.user_type != 'client':
            raise PermissionError('Only clients can register pets')
        serializer.save(owner=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete - set is_active to False instead of deleting"""
        instance.is_active = False
        instance.save()
    
    @swagger_auto_schema(
        operation_description="Get complete medical history for a pet",
        responses={200: 'List of medical records'}
    )
    @action(detail=True, methods=['get'])
    def medical_history(self, request, pk=None):
        """Get all medical records for this pet"""
        pet = self.get_object()
        
        from apps.medical_records.models import MedicalRecord
        from apps.medical_records.serializers import MedicalRecordSerializer
        
        records = MedicalRecord.objects.filter(pet=pet).order_by('-date')
        serializer = MedicalRecordSerializer(records, many=True)
        
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get vaccination records for a pet",
        responses={200: 'List of vaccinations'}
    )
    @action(detail=True, methods=['get'])
    def vaccinations(self, request, pk=None):
        """Get all vaccination records for this pet"""
        pet = self.get_object()
        
        from apps.medical_records.models import Vaccination
        from apps.medical_records.serializers import VaccinationSerializer
        
        vaccinations = Vaccination.objects.filter(pet=pet).order_by('-date_administered')
        serializer = VaccinationSerializer(vaccinations, many=True)
        
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get appointment history for a pet",
        responses={200: 'List of appointments'}
    )
    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        """Get all appointments for this pet"""
        pet = self.get_object()
        
        from apps.appointments.models import Appointment
        from apps.appointments.serializers import AppointmentListSerializer
        
        appointments = Appointment.objects.filter(pet=pet).order_by('-appointment_date')
        serializer = AppointmentListSerializer(appointments, many=True)
        
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get pet health summary",
        responses={200: 'Pet health summary'}
    )
    @action(detail=True, methods=['get'])
    def health_summary(self, request, pk=None):
        """Get comprehensive health summary for a pet"""
        pet = self.get_object()
        
        from apps.medical_records.models import MedicalRecord, Vaccination
        from apps.appointments.models import Appointment
        
        # Get latest medical record
        latest_record = MedicalRecord.objects.filter(pet=pet).order_by('-date').first()
        
        # Get upcoming vaccinations
        from django.utils import timezone
        upcoming_vaccinations = Vaccination.objects.filter(
            pet=pet,
            next_due_date__gte=timezone.now().date()
        ).order_by('next_due_date')[:3]
        
        # Get appointment stats
        total_appointments = Appointment.objects.filter(pet=pet).count()
        completed_appointments = Appointment.objects.filter(
            pet=pet,
            status='completed'
        ).count()
        
        # Check for overdue vaccinations
        overdue_vaccinations = Vaccination.objects.filter(
            pet=pet,
            next_due_date__lt=timezone.now().date()
        ).count()
        
        summary = {
            'pet_info': PetSerializer(pet).data,
            'latest_medical_record': {
                'date': latest_record.date if latest_record else None,
                'diagnosis': latest_record.diagnosis if latest_record else None,
                'vet': latest_record.vet.get_full_name() if latest_record else None
            } if latest_record else None,
            'upcoming_vaccinations': [
                {
                    'vaccine_name': v.vaccine_name,
                    'due_date': v.next_due_date
                } for v in upcoming_vaccinations
            ],
            'overdue_vaccinations_count': overdue_vaccinations,
            'appointment_stats': {
                'total': total_appointments,
                'completed': completed_appointments
            },
            'health_alerts': []
        }
        
        # Add health alerts
        if overdue_vaccinations > 0:
            summary['health_alerts'].append({
                'type': 'warning',
                'message': f'{overdue_vaccinations} vaccination(s) overdue'
            })
        
        if latest_record and latest_record.follow_up_required:
            summary['health_alerts'].append({
                'type': 'info',
                'message': f'Follow-up required on {latest_record.follow_up_date}'
            })
        
        return Response(summary)
    
    @swagger_auto_schema(
        operation_description="Get pets by species",
        manual_parameters=[
            openapi.Parameter(
                'species',
                openapi.IN_QUERY,
                description="Pet species (dog, cat, bird, etc.)",
                type=openapi.TYPE_STRING,
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_species(self, request):
        """Get all pets of a specific species"""
        species = request.query_params.get('species')
        
        if not species:
            return Response(
                {'error': 'species parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        pets = self.get_queryset().filter(species=species)
        serializer = self.get_serializer(pets, many=True)
        
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get active pets only",
        responses={200: 'List of active pets'}
    )
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active pets"""
        pets = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(pets, many=True)
        
        return Response(serializer.data)