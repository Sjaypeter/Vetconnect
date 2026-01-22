from rest_framework import serializers
from django.utils import timezone
from .models import Pet


class PetSerializer(serializers.ModelSerializer):
    """Serializer for Pet model"""
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    age_months = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Pet
        fields = ['id', 'owner', 'owner_name', 'name', 'species', 'breed', 
                  'date_of_birth', 'gender', 'weight', 'color', 'microchip_number', 
                  'photo', 'allergies', 'medical_notes', 'is_active', 
                  'age', 'age_months', 'created_at', 'updated_at']
        read_only_fields = ['owner', 'created_at', 'updated_at']
    
    def validate_date_of_birth(self, value):
        """Validate date of birth is not in the future"""
        if value > timezone.now().date():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        
        # Check if pet is not too old (e.g., max 50 years)
        age = timezone.now().date().year - value.year
        if age > 50:
            raise serializers.ValidationError("Please check the date of birth.")
        
        return value
    
    def validate_weight(self, value):
        """Validate weight is positive"""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than zero.")
        if value > 500:  # Maximum weight in kg
            raise serializers.ValidationError("Weight seems too high. Please verify.")
        return value


class PetListSerializer(serializers.ModelSerializer):
    """Simplified serializer for pet list view"""
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Pet
        fields = ['id', 'owner_name', 'name', 'species', 'breed', 
                  'age', 'photo', 'is_active']