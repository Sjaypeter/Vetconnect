# api/v1/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

# Import ViewSets from each app
from apps.accounts.views import (
    UserViewSet, VetProfileViewSet, ClientProfileViewSet,
    RegisterView, LogoutView, CurrentUserView, ChangePasswordView
)
from apps.pets.views import PetViewSet
from apps.appointments.views import AppointmentViewSet
from apps.medical_records.views import MedicalRecordViewSet, VaccinationViewSet, PrescriptionViewSet
from apps.notifications.views import NotificationViewSet
from apps.chat.views import ChatMessageViewSet
from apps.reviews.views import ReviewViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'vets', VetProfileViewSet, basename='vet')
router.register(r'clients', ClientProfileViewSet, basename='client')
router.register(r'pets', PetViewSet, basename='pet')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')
router.register(r'vaccinations', VaccinationViewSet, basename='vaccination')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'messages', ChatMessageViewSet, basename='message')
router.register(r'reviews', ReviewViewSet, basename='review')

app_name = 'api_v1'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', obtain_auth_token, name='auth_login'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/user/', CurrentUserView.as_view(), name='current_user'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Router URLs
    path('', include(router.urls)),
]