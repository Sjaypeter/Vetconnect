from rest_framework import serializers
from .models import Review, ReviewHelpful


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model"""
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_profile_picture = serializers.ImageField(source='client.profile_picture', read_only=True)
    vet_name = serializers.CharField(source='vet.get_full_name', read_only=True)
    appointment_date = serializers.DateTimeField(
        source='appointment.appointment_date',
        read_only=True
    )
    helpful_count = serializers.SerializerMethodField()
    is_helpful_by_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = [
            'id', 'vet', 'vet_name', 'client', 'client_name',
            'client_profile_picture', 'appointment', 'appointment_date',
            'rating', 'comment', 'communication_rating',
            'professionalism_rating', 'care_quality_rating',
            'would_recommend', 'is_approved', 'is_flagged',
            'vet_response', 'vet_response_date', 'helpful_count',
            'is_helpful_by_user', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'client', 'is_approved', 'is_flagged',
            'vet_response', 'vet_response_date',
            'created_at', 'updated_at'
        ]
    
    def get_helpful_count(self, obj):
        """Get count of helpful votes"""
        return obj.helpful_votes.count()
    
    def get_is_helpful_by_user(self, obj):
        """Check if current user marked this as helpful"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ReviewHelpful.objects.filter(
                review=obj,
                user=request.user
            ).exists()
        return False


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    
    class Meta:
        model = Review
        fields = [
            'vet', 'appointment', 'rating', 'comment',
            'communication_rating', 'professionalism_rating',
            'care_quality_rating', 'would_recommend'
        ]
    
    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
    def validate_appointment(self, value):
        """Validate appointment conditions"""
        request = self.context['request']
        
        # Check if user is the client
        if value.client != request.user:
            raise serializers.ValidationError(
                "You can only review your own appointments"
            )
        
        # Check if appointment is completed
        if value.status != 'completed':
            raise serializers.ValidationError(
                "You can only review completed appointments"
            )
        
        # Check if review already exists
        if Review.objects.filter(appointment=value).exists():
            raise serializers.ValidationError(
                "You have already reviewed this appointment"
            )
        
        return value
    
    def validate(self, attrs):
        """Validate vet matches appointment"""
        appointment = attrs.get('appointment')
        vet = attrs.get('vet')
        
        if appointment and vet and appointment.vet != vet:
            raise serializers.ValidationError({
                'vet': 'Vet must match the appointment veterinarian'
            })
        
        # Auto-set vet from appointment if not provided
        if appointment and not vet:
            attrs['vet'] = appointment.vet
        
        return attrs


class ReviewStatsSerializer(serializers.Serializer):
    """Serializer for review statistics"""
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField()
    would_recommend_percentage = serializers.FloatField()
    average_communication = serializers.FloatField()
    average_professionalism = serializers.FloatField()
    average_care_quality = serializers.FloatField()