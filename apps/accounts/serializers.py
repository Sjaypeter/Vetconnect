# apps/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, VetProfile, ClientProfile


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'full_name', 'user_type', 'phone', 'profile_picture', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VetProfileSerializer(serializers.ModelSerializer):
    """Serializer for Vet Profile"""
    user = UserSerializer(read_only=True)
    avg_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = VetProfile
        fields = ['id', 'user', 'specialization', 'license_number', 
                  'years_of_experience', 'bio', 'consultation_fee', 
                  'available_days', 'available_hours', 'is_verified', 
                  'rating', 'avg_rating', 'total_reviews', 'total_consultations',
                  'created_at', 'updated_at']
        read_only_fields = ['is_verified', 'rating', 'total_consultations']
    
    def get_avg_rating(self, obj):
        from django.db.models import Avg
        from apps.reviews.models import Review
        avg = Review.objects.filter(vet=obj.user).aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0
    
    def get_total_reviews(self, obj):
        from apps.reviews.models import Review
        return Review.objects.filter(vet=obj.user).count()


class ClientProfileSerializer(serializers.ModelSerializer):
    """Serializer for Client Profile"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = ['id', 'user', 'address', 'emergency_contact', 
                  'preferred_language', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    # Vet-specific fields
    specialization = serializers.CharField(required=False, allow_blank=True)
    license_number = serializers.CharField(required=False, allow_blank=True)
    years_of_experience = serializers.IntegerField(required=False, default=0)
    bio = serializers.CharField(required=False, allow_blank=True)
    consultation_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )
    
    # Client-specific fields
    address = serializers.CharField(required=False, allow_blank=True)
    emergency_contact = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 
                  'last_name', 'phone', 'user_type', 'profile_picture',
                  'specialization', 'license_number', 'years_of_experience', 
                  'bio', 'consultation_fee', 'address', 'emergency_contact']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate vet-specific fields
        if attrs.get('user_type') == 'vet':
            if not attrs.get('specialization'):
                raise serializers.ValidationError({"specialization": "Required for vets."})
            if not attrs.get('license_number'):
                raise serializers.ValidationError({"license_number": "Required for vets."})
        
        return attrs
    
    def create(self, validated_data):
        # Remove extra fields
        validated_data.pop('password2')
        specialization = validated_data.pop('specialization', '')
        license_number = validated_data.pop('license_number', '')
        years_of_experience = validated_data.pop('years_of_experience', 0)
        bio = validated_data.pop('bio', '')
        consultation_fee = validated_data.pop('consultation_fee', 0)
        address = validated_data.pop('address', '')
        emergency_contact = validated_data.pop('emergency_contact', '')
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        # Create profile based on user type
        if user.user_type == 'vet':
            VetProfile.objects.create(
                user=user,
                specialization=specialization,
                license_number=license_number,
                years_of_experience=years_of_experience,
                bio=bio,
                consultation_fee=consultation_fee
            )
        else:
            ClientProfile.objects.create(
                user=user,
                address=address,
                emergency_contact=emergency_contact
            )
        
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])