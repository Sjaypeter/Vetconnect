# api/v1/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from apps.accounts.views import (
    UserViewSet, VetProfileViewSet, ClientProfileViewSet,
    RegisterView, LogoutView, CurrentUserView, ChangePasswordView
)
from apps.pets.views import PetViewSet
from apps.appointments.views import AppointmentViewSet
from apps.medical_records.views import (
    MedicalRecordViewSet, VaccinationViewSet, PrescriptionViewSet
)
from apps.notifications.views import (
    NotificationViewSet, EmailLogViewSet, SMSLogViewSet
)
from apps.chat.views import ChatMessageViewSet, ChatRoomViewSet, RoomMessageViewSet
from apps.reviews.views import ReviewViewSet

from apps.payments.views import (
    PaymentViewSet, InvoiceViewSet, RefundViewSet,
    PaymentMethodViewSet, WalletViewSet
)
router = DefaultRouter()

# Accounts
router.register(r'users', UserViewSet, basename='user')
router.register(r'vets', VetProfileViewSet, basename='vet')
router.register(r'clients', ClientProfileViewSet, basename='client')

# Pets
router.register(r'pets', PetViewSet, basename='pet')

# Appointments
router.register(r'appointments', AppointmentViewSet, basename='appointment')

# Medical Records
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')
router.register(r'vaccinations', VaccinationViewSet, basename='vaccination')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')

# Notifications
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'email-logs', EmailLogViewSet, basename='email-log')
router.register(r'sms-logs', SMSLogViewSet, basename='sms-log')

# Chat
router.register(r'messages', ChatMessageViewSet, basename='message')
router.register(r'chat-rooms', ChatRoomViewSet, basename='chat-room')
router.register(r'room-messages', RoomMessageViewSet, basename='room-message')

# Reviews
router.register(r'reviews', ReviewViewSet, basename='review')

#Payments
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'wallets', WalletViewSet, basename='wallet')

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