from rest_framework import serializers
from django.utils import timezone
from .models import Appointment
from apps.pets.serializers import PetSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model"""
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    vet_name = serializers.CharField(source='vet.get_full_name', read_only=True)
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    pet_details = PetSerializer(source='pet', read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'client', 'client_name', 'vet', 'vet_name', 
            'pet', 'pet_name', 'pet_details', 'appointment_date', 
            'duration', 'status', 'reason', 'symptoms',
            'meeting_link', 'meeting_id', 'meeting_password',
            'notes', 'prescription', 'follow_up_required', 'follow_up_date',
            'cancelled_by', 'cancellation_reason', 'cancellation_note', 'cancelled_at',
            'is_upcoming', 'is_past', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'client', 'meeting_link', 'meeting_id', 'meeting_password',
            'cancelled_by', 'cancelled_at', 'created_at', 'updated_at'
        ]
    
    def validate_appointment_date(self, value):
        """Validate appointment date"""
        if value < timezone.now():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        
        # Check if it's too far in the future (e.g., max 6 months)
        six_months = timezone.now() + timezone.timedelta(days=180)
        if value > six_months:
            raise serializers.ValidationError("Cannot book more than 6 months in advance.")
        
        return value
    
    def validate(self, attrs):
        """Validate appointment data"""
        # Check if pet belongs to client
        if self.context['request'].user.user_type == 'client':
            pet = attrs.get('pet')
            if pet and pet.owner != self.context['request'].user:
                raise serializers.ValidationError({
                    "pet": "You can only book appointments for your own pets."
                })
        
        # Check if vet is available (you can add more complex logic here)
        appointment_date = attrs.get('appointment_date')
        vet = attrs.get('vet')
        
        if appointment_date and vet:
            # Check for overlapping appointments
            overlapping = Appointment.objects.filter(
                vet=vet,
                appointment_date=appointment_date,
                status__in=['pending', 'confirmed']
            )
            
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            
            if overlapping.exists():
                raise serializers.ValidationError({
                    "appointment_date": "This time slot is not available."
                })
        
        return attrs


class AppointmentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for appointment list"""
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    vet_name = serializers.CharField(source='vet.get_full_name', read_only=True)
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'client_name', 'vet_name', 'pet_name',
            'appointment_date', 'duration', 'status', 'created_at'
        ]


class AppointmentCancelSerializer(serializers.Serializer):
    """Serializer for cancelling appointments"""
    reason = serializers.ChoiceField(choices=Appointment.CANCELLATION_REASON_CHOICES)
    note = serializers.CharField(required=False, allow_blank=True)