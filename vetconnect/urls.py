from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="VetConnect API",
        default_version='v1',
        description="""
        # VetConnect - Veterinary Telemedicine Platform API
        
        Complete API documentation for the VetConnect platform.
        
        ## Features:
        - 👥 User Authentication (Client & Vet registration)
        - 🐾 Pet Profile Management
        - 📅 Appointment Booking & Scheduling
        - 🎥 Video Consultation Integration
        - 💬 Real-time Chat System
        - 📋 Medical Records Management
        - 💉 Vaccination Tracking
        - ⭐ Review & Rating System
        - 🔔 Automated Notifications (Email & SMS)
        
        ## Authentication:
        This API uses Token Authentication. 
        
        **To get your token:**
        1. Register using `/api/v1/auth/register/`
        2. Login using `/api/v1/auth/login/`
        3. Use the token in the header: `Authorization: Token <your-token>`
        
        ## Rate Limits:
        - Authenticated users: 1000 requests per hour
        - Anonymous users: 100 requests per hour
        """,
        terms_of_service="https://www.vetconnect.com/terms/",
        contact=openapi.Contact(email="support@vetconnect.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),
    
    # API Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', 
            schema_view.without_ui(cache_timeout=0), 
            name='schema-json'),
    path('swagger/', 
         schema_view.with_ui('swagger', cache_timeout=0), 
         name='schema-swagger-ui'),
    path('redoc/', 
         schema_view.with_ui('redoc', cache_timeout=0), 
         name='schema-redoc'),
    
    # API v1
    path('api/v1/', include('api.v1.urls')),
    
    # DRF Auth (for browsable API)
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site header
admin.site.site_header = "VetConnect Administration"
admin.site.site_title = "VetConnect Admin"
admin.site.index_title = "Welcome to VetConnect Administration"