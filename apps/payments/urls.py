from django.urls import path
from .webhooks import stripe_webhook

app_name = 'payments'

urlpatterns = [
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),
]


