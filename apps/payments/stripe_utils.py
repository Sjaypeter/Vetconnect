import stripe
from django.conf import settings
from django.utils import timezone
import uuid
from .models import Payment, PaymentMethod, Refund

# Initialize Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class StripePaymentService:
    """Service class for handling Stripe payments"""
    
    def __init__(self):
        self.api_key = stripe.api_key
    
    def get_or_create_customer(self, user):
        """Get or create Stripe customer for user"""
        # Check if user already has a Stripe customer ID
        if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                return customer
            except stripe.error.StripeError:
                pass
        
        # Create new customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.get_full_name(),
            phone=user.phone if hasattr(user, 'phone') else None,
            metadata={
                'user_id': user.id,
                'username': user.username
            }
        )
        
        # Save customer ID to user
        # Note: I might need to add stripe_customer_id field to User model
        # user.stripe_customer_id = customer.id
        # user.save()
        
        return customer
    
    def create_payment_intent(self, amount, currency='usd', customer_id=None, 
                            payment_method_id=None, metadata=None):
        """Create Stripe payment intent"""
        try:
            params = {
                'amount': int(amount * 100),  # Convert to cents
                'currency': currency,
                'metadata': metadata or {},
            }
            
            if customer_id:
                params['customer'] = customer_id
            
            if payment_method_id:
                params['payment_method'] = payment_method_id
                params['confirm'] = True
                params['automatic_payment_methods'] = {
                    'enabled': True,
                    'allow_redirects': 'never'
                }
            
            payment_intent = stripe.PaymentIntent.create(**params)
            return payment_intent
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_payment(self, user, amount, appointment_id=None, 
                      payment_method_id=None, description='', 
                      save_payment_method=False):
        """Create payment with Stripe"""
        try:
            # Get or create Stripe customer
            customer = self.get_or_create_customer(user)
            
            # Generate unique transaction ID
            transaction_id = f"TXN-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            # Create metadata
            metadata = {
                'user_id': user.id,
                'transaction_id': transaction_id,
            }
            if appointment_id:
                metadata['appointment_id'] = appointment_id
            
            # Create payment intent
            payment_intent = self.create_payment_intent(
                amount=amount,
                customer_id=customer.id,
                payment_method_id=payment_method_id,
                metadata=metadata
            )
            
            # Create payment record
            payment = Payment.objects.create(
                user=user,
                appointment_id=appointment_id,
                amount=amount,
                currency='USD',
                payment_method='card',
                status='processing' if payment_intent.status == 'processing' else 'pending',
                transaction_id=transaction_id,
                description=description,
                stripe_payment_intent_id=payment_intent.id,
                stripe_customer_id=customer.id,
                metadata=metadata
            )
            
            # Check payment status
            if payment_intent.status == 'succeeded':
                payment.mark_as_paid()
            
            # Save payment method if requested
            if save_payment_method and payment_method_id:
                self._save_payment_method(user, payment_method_id, customer.id)
            
            return payment
            
        except stripe.error.StripeError as e:
            raise Exception(f"Payment failed: {str(e)}")
    
    def verify_payment(self, payment):
        """Verify payment status with Stripe"""
        try:
            if not payment.stripe_payment_intent_id:
                raise Exception("No Stripe payment intent ID found")
            
            payment_intent = stripe.PaymentIntent.retrieve(
                payment.stripe_payment_intent_id
            )
            
            # Update payment status
            if payment_intent.status == 'succeeded':
                payment.status = 'completed'
                if not payment.paid_at:
                    payment.paid_at = timezone.now()
            elif payment_intent.status == 'processing':
                payment.status = 'processing'
            elif payment_intent.status in ['canceled', 'failed']:
                payment.status = 'failed'
            
            payment.save()
            return payment
            
        except stripe.error.StripeError as e:
            raise Exception(f"Verification failed: {str(e)}")
    
    def add_payment_method(self, user, stripe_payment_method_id, is_default=False):
        """Add payment method to user account"""
        try:
            # Get or create customer
            customer = self.get_or_create_customer(user)
            
            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                stripe_payment_method_id,
                customer=customer.id
            )
            
            # Get card details
            card = payment_method.card
            
            # Create payment method record
            pm = PaymentMethod.objects.create(
                user=user,
                card_type=card.brand,
                last_four=card.last4,
                expiry_month=card.exp_month,
                expiry_year=card.exp_year,
                cardholder_name=payment_method.billing_details.name or user.get_full_name(),
                stripe_payment_method_id=payment_method.id,
                stripe_customer_id=customer.id,
                is_default=is_default
            )
            
            # Set as default if requested
            if is_default:
                stripe.Customer.modify(
                    customer.id,
                    invoice_settings={
                        'default_payment_method': payment_method.id
                    }
                )
            
            return pm
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to add payment method: {str(e)}")
    
    def remove_payment_method(self, payment_method):
        """Remove payment method"""
        try:
            # Detach from Stripe
            stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
            
            # Soft delete
            payment_method.is_active = False
            payment_method.save()
            
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to remove payment method: {str(e)}")
    
    def process_refund(self, refund):
        """Process refund with Stripe"""
        try:
            payment = refund.payment
            
            if not payment.stripe_payment_intent_id:
                raise Exception("No Stripe payment intent ID found")
            
            # Create Stripe refund
            stripe_refund = stripe.Refund.create(
                payment_intent=payment.stripe_payment_intent_id,
                amount=int(refund.amount * 100),  # Convert to cents
                reason=self._get_stripe_refund_reason(refund.reason),
                metadata={
                    'refund_id': refund.id,
                    'user_id': payment.user.id
                }
            )
            
            # Update refund
            refund.stripe_refund_id = stripe_refund.id
            refund.status = 'completed'
            refund.processed_at = timezone.now()
            refund.save()
            
            # Update payment
            payment.status = 'refunded'
            payment.save()
            
            return refund
            
        except stripe.error.StripeError as e:
            refund.status = 'failed'
            refund.description = f"Refund failed: {str(e)}"
            refund.save()
            raise Exception(f"Refund failed: {str(e)}")
    
    def _get_stripe_refund_reason(self, reason):
        """Map internal refund reason to Stripe refund reason"""
        mapping = {
            'duplicate': 'duplicate',
            'fraudulent': 'fraudulent',
            'requested_by_customer': 'requested_by_customer',
        }
        return mapping.get(reason, 'requested_by_customer')
    
    def _save_payment_method(self, user, payment_method_id, customer_id):
        """Internal method to save payment method"""
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            card = payment_method.card
            
            PaymentMethod.objects.create(
                user=user,
                card_type=card.brand,
                last_four=card.last4,
                expiry_month=card.exp_month,
                expiry_year=card.exp_year,
                cardholder_name=payment_method.billing_details.name or user.get_full_name(),
                stripe_payment_method_id=payment_method.id,
                stripe_customer_id=customer_id,
                is_default=False
            )
        except stripe.error.StripeError:
            pass  # Silently fail if payment method save fails


class StripeWebhookHandler:
    """Handler for Stripe webhooks"""
    
    @staticmethod
    def handle_payment_intent_succeeded(payment_intent):
        """Handle successful payment intent"""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent.id
            )
            payment.mark_as_paid()
            
            # Send notification to user
            from apps.notifications.models import Notification
            Notification.objects.create(
                user=payment.user,
                notification_type='system',
                priority='medium',
                title='Payment Successful',
                message=f'Your payment of ${payment.amount} has been processed successfully',
                link=f'/api/v1/payments/{payment.id}/'
            )
            
        except Payment.DoesNotExist:
            pass
    
    @staticmethod
    def handle_payment_intent_failed(payment_intent):
        """Handle failed payment intent"""
        try:
            payment = Payment.objects.get(
                stripe_payment_intent_id=payment_intent.id
            )
            payment.status = 'failed'
            payment.save()
            
            # Send notification to user
            from apps.notifications.models import Notification
            Notification.objects.create(
                user=payment.user,
                notification_type='system',
                priority='high',
                title='Payment Failed',
                message=f'Your payment of ${payment.amount} has failed. Please try again.',
                link=f'/api/v1/payments/{payment.id}/'
            )
            
        except Payment.DoesNotExist:
            pass
    
    @staticmethod
    def handle_refund_updated(refund_data):
        """Handle refund status update"""
        try:
            refund = Refund.objects.get(
                stripe_refund_id=refund_data.id
            )
            
            if refund_data.status == 'succeeded':
                refund.status = 'completed'
                refund.processed_at = timezone.now()
            elif refund_data.status == 'failed':
                refund.status = 'failed'
            
            refund.save()
            
        except Refund.DoesNotExist:
            pass