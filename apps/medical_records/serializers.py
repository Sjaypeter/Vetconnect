from rest_framework import serializers
from .models import MedicalRecord, Vaccination, Prescription


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer for Prescription model"""
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'medical_record', 'medication_name', 'dosage',
            'frequency', 'duration', 'quantity', 'instructions',
            'start_date', 'end_date', 'created_at'
        ]
        read_only_fields = ['created_at']


class MedicalRecordSerializer(serializers.ModelSerializer):
    """Serializer for Medical Record model"""
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    vet_name = serializers.CharField(source='vet.get_full_name', read_only=True)
    prescription_items = PrescriptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'pet', 'pet_name', 'vet', 'vet_name', 'appointment',
            'date', 'diagnosis', 'treatment', 'prescriptions', 'test_results',
            'follow_up_required', 'follow_up_date', 'follow_up_instructions',
            'attachments', 'temperature', 'heart_rate', 'respiratory_rate',
            'weight', 'prescription_items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['vet', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate medical record data"""
        if attrs.get('follow_up_required') and not attrs.get('follow_up_date'):
            raise serializers.ValidationError({
                'follow_up_date': 'Follow-up date is required when follow-up is needed'
            })
        
        # Validate vitals
        temperature = attrs.get('temperature')
        if temperature and (temperature < 30 or temperature > 45):
            raise serializers.ValidationError({
                'temperature': 'Temperature seems abnormal. Please verify.'
            })
        
        heart_rate = attrs.get('heart_rate')
        if heart_rate and (heart_rate < 20 or heart_rate > 300):
            raise serializers.ValidationError({
                'heart_rate': 'Heart rate seems abnormal. Please verify.'
            })
        
        return attrs


class MedicalRecordListSerializer(serializers.ModelSerializer):
    """Simplified serializer for medical record list"""
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    vet_name = serializers.CharField(source='vet.get_full_name', read_only=True)
    
    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'pet_name', 'vet_name', 'date',
            'diagnosis', 'follow_up_required', 'created_at'
        ]


class VaccinationSerializer(serializers.ModelSerializer):
    """Serializer for Vaccination model"""
    pet_name = serializers.CharField(source='pet.name', read_only=True)
    administered_by_name = serializers.CharField(
        source='administered_by.get_full_name',
        read_only=True
    )
    is_due_soon = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Vaccination
        fields = [
            'id', 'pet', 'pet_name', 'vaccine_name', 'vaccine_type',
            'date_administered', 'next_due_date', 'administered_by',
            'administered_by_name', 'batch_number', 'manufacturer',
            'notes', 'reminder_sent', 'is_due_soon', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['administered_by', 'reminder_sent', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate vaccination data"""
        next_due = attrs.get('next_due_date')
        date_admin = attrs.get('date_administered')
        
        if next_due and date_admin and next_due <= date_admin:
            raise serializers.ValidationError({
                'next_due_date': 'Next due date must be after administration date'
            })
        
        return attrs