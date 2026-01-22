# apps/accounts/views.py
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Avg, Q
from .models import User, VetProfile, ClientProfile
from .serializers import (
    UserSerializer, VetProfileSerializer, ClientProfileSerializer,
    UserRegistrationSerializer, ChangePasswordSerializer
)


class RegisterView(generics.CreateAPIView):
    """
    Register a new user (Client or Veterinarian)
    
    Creates a new user account and returns authentication token.
    User profile is automatically created based on user_type.
    """
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserRegistrationSerializer
    
    @swagger_auto_schema(
        operation_description="Register a new user",
        responses={
            201: openapi.Response(
                'User created successfully',
                UserSerializer
            ),
            400: 'Bad Request - Validation errors'
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create authentication token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """
    Logout current user
    
    Deletes the authentication token and logs out the user.
    """
    permission_classes = (IsAuthenticated,)
    
    @swagger_auto_schema(
        operation_description="Logout user and delete authentication token",
        responses={
            200: 'Successfully logged out',
            401: 'Unauthorized - Invalid token'
        }
    )
    def post(self, request):
        try:
            # Delete user's token
            request.user.auth_token.delete()
            logout(request)
            return Response({
                'message': 'Successfully logged out'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    Get or update current authenticated user profile
    
    retrieve: Get current user details
    update: Update current user profile
    partial_update: Partially update current user profile
    """
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    
    def get_object(self):
        return self.request.user
    
    @swagger_auto_schema(
        operation_description="Get current user profile"
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update current user profile"
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update current user profile"
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ChangePasswordView(APIView):
    """
    Change password for authenticated user
    
    Requires old password verification before setting new password.
    """
    permission_classes = (IsAuthenticated,)
    
    @swagger_auto_schema(
        operation_description="Change user password",
        request_body=ChangePasswordSerializer,
        responses={
            200: 'Password changed successfully',
            400: 'Bad Request - Invalid old password or validation error'
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')
            
            # Verify old password
            if not user.check_password(old_password):
                return Response({
                    'error': 'Old password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            # Update token (optional - forces re-login)
            # Token.objects.filter(user=user).delete()
            # Token.objects.create(user=user)
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for users (read-only)
    
    list: Get list of users
    retrieve: Get specific user details
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user_type', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    def get_queryset(self):
        """Filter users based on user type"""
        queryset = User.objects.all()
        user_type = self.request.query_params.get('user_type')
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        return queryset


class VetProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for veterinarian profiles
    
    list: Get list of all verified veterinarians
    retrieve: Get specific veterinarian details
    reviews: Get reviews for a veterinarian
    available_slots: Get available appointment slots
    search: Search vets by specialization
    """
    queryset = VetProfile.objects.filter(is_verified=True)
    serializer_class = VetProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['specialization', 'is_verified']
    search_fields = ['user__first_name', 'user__last_name', 'specialization', 'bio']
    ordering_fields = ['rating', 'years_of_experience', 'consultation_fee', 'total_consultations']
    ordering = ['-rating']
    
    @swagger_auto_schema(
        operation_description="Get all reviews for a veterinarian",
        responses={200: 'List of reviews'}
    )
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all reviews for this veterinarian"""
        vet_profile = self.get_object()
        from apps.reviews.models import Review
        from apps.reviews.serializers import ReviewSerializer
        
        reviews = Review.objects.filter(
            vet=vet_profile.user,
            is_approved=True
        ).order_by('-created_at')
        
        serializer = ReviewSerializer(reviews, many=True, context={'request': request})
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get available appointment slots for a date",
        manual_parameters=[
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Date in YYYY-MM-DD format",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={200: 'List of available time slots'}
    )
    @action(detail=True, methods=['get'])
    def available_slots(self, request, pk=None):
        """Get available appointment slots for a specific date"""
        from datetime import datetime, timedelta
        from apps.appointments.models import Appointment
        
        vet_profile = self.get_object()
        date_str = request.query_params.get('date')
        
        if not date_str:
            return Response(
                {'error': 'Date parameter is required (YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get day name
        day_name = selected_date.strftime('%A')
        
        # Check if vet is available on this day
        if day_name not in vet_profile.available_days:
            return Response({
                'date': date_str,
                'available': False,
                'message': f'Veterinarian is not available on {day_name}s',
                'slots': []
            })
        
        # Get vet's working hours
        available_hours = vet_profile.available_hours
        start_hour = int(available_hours.get('start', '09:00').split(':')[0])
        end_hour = int(available_hours.get('end', '17:00').split(':')[0])
        
        # Get existing appointments for this date
        existing_appointments = Appointment.objects.filter(
            vet=vet_profile.user,
            appointment_date__date=selected_date,
            status__in=['pending', 'confirmed']
        ).values_list('appointment_date', flat=True)
        
        # Generate time slots (30-minute intervals)
        slots = []
        current_time = datetime.combine(selected_date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(selected_date, datetime.min.time().replace(hour=end_hour))
        
        while current_time < end_time:
            # Check if slot is already booked
            is_booked = any(
                appt.hour == current_time.hour and appt.minute == current_time.minute
                for appt in existing_appointments
            )
            
            slots.append({
                'time': current_time.strftime('%H:%M'),
                'available': not is_booked
            })
            
            current_time += timedelta(minutes=30)
        
        return Response({
            'date': date_str,
            'day': day_name,
            'available': True,
            'slots': slots
        })
    
    @swagger_auto_schema(
        operation_description="Get veterinarian statistics",
        responses={200: 'Veterinarian statistics'}
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for a veterinarian"""
        vet_profile = self.get_object()
        from apps.appointments.models import Appointment
        from apps.reviews.models import Review
        
        total_appointments = Appointment.objects.filter(vet=vet_profile.user).count()
        completed_appointments = Appointment.objects.filter(
            vet=vet_profile.user,
            status='completed'
        ).count()
        
        reviews = Review.objects.filter(vet=vet_profile.user, is_approved=True)
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        return Response({
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 2),
            'years_of_experience': vet_profile.years_of_experience,
            'specialization': vet_profile.specialization
        })


class ClientProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for client profiles
    
    list: Get list of client profiles (admin only)
    retrieve: Get specific client profile
    """
    queryset = ClientProfile.objects.all()
    serializer_class = ClientProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own profile"""
        user = self.request.user
        if user.is_staff:
            return ClientProfile.objects.all()
        return ClientProfile.objects.filter(user=user)