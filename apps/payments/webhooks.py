from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe
import json
from .stripe_utils import StripeWebhookHandler

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle the event
    handler = StripeWebhookHandler()
    
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handler.handle_payment_intent_succeeded(payment_intent)
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handler.handle_payment_intent_failed(payment_intent)
    
    elif event['type'] == 'charge.refunded':
        refund = event['data']['object']
        handler.handle_refund_updated(refund)
    
    return HttpResponse(status=200)


# Update api/v1/urls.py to include payment routes
"""
Add to api/v1/urls.py:

from apps.payments.views import (
    PaymentViewSet, InvoiceViewSet, RefundViewSet,
    PaymentMethodViewSet, WalletViewSet
)

# In router registration:
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'wallets', WalletViewSet, basename='wallet')
"""


# Update settings.py to include payments app
"""
Add to INSTALLED_APPS in settings.py:

LOCAL_APPS = [
    # ... other apps
    'apps.payments.apps.PaymentsConfig',
]

# Add Stripe configuration
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')
"""


# Update main urls.py to include payment webhooks
"""
Add to main urlpatterns in vetconnect/urls.py:

urlpatterns = [
    # ... other patterns
    path('payments/', include('apps.payments.urls')),
]
"""