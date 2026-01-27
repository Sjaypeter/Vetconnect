from vetconnect.celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta, date
from .models import Payment, Invoice, PaymentMethod, Refund
from apps.notifications.models import Notification


@shared_task(name='apps.payments.tasks.send_invoice_reminders')
def send_invoice_reminders():
    """
    Send reminders for unpaid invoices
    Runs daily at 8 AM
    """
    today = timezone.now().date()
    
    # Get invoices due within 3 days
    upcoming_due = Invoice.objects.filter(
        status__in=['sent', 'draft'],
        due_date__gte=today,
        due_date__lte=today + timedelta(days=3)
    )
    
    # Get overdue invoices
    overdue = Invoice.objects.filter(
        status='sent',
        due_date__lt=today
    )
    
    sent_count = 0
    
    # Send reminders for upcoming due invoices
    for invoice in upcoming_due:
        days_until_due = (invoice.due_date - today).days
        
        try:
            send_mail(
                subject=f'Invoice Due Reminder - {invoice.invoice_number}',
                message=f"""
Hello {invoice.user.get_full_name()},

This is a reminder that invoice {invoice.invoice_number} is due in {days_until_due} days.

Invoice Details:
Amount: {invoice.currency} {invoice.total}
Due Date: {invoice.due_date.strftime('%B %d, %Y')}

Please ensure payment is made by the due date.

View invoice: {settings.FRONTEND_URL}/invoices/{invoice.id}

Best regards,
VetConnect Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invoice.user.email],
                fail_silently=True,
            )
            
            # Create notification
            Notification.objects.create(
                user=invoice.user,
                notification_type='system',
                priority='medium',
                title='Invoice Due Soon',
                message=f'Invoice {invoice.invoice_number} is due in {days_until_due} days',
                link=f'/api/v1/invoices/{invoice.id}/'
            )
            
            sent_count += 1
            
        except Exception as e:
            print(f"Error sending invoice reminder: {e}")
    
    # Send overdue notifications
    for invoice in overdue:
        days_overdue = (today - invoice.due_date).days
        
        # Update status to overdue
        invoice.status = 'overdue'
        invoice.save()
        
        try:
            send_mail(
                subject=f'OVERDUE INVOICE - {invoice.invoice_number}',
                message=f"""
Hello {invoice.user.get_full_name()},

IMPORTANT: Invoice {invoice.invoice_number} is now {days_overdue} days overdue.

Invoice Details:
Amount: {invoice.currency} {invoice.total}
Due Date: {invoice.due_date.strftime('%B %d, %Y')}

Please make payment as soon as possible to avoid service interruption.

View invoice: {settings.FRONTEND_URL}/invoices/{invoice.id}

Best regards,
VetConnect Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invoice.user.email],
                fail_silently=True,
            )
            
            # Create high priority notification
            Notification.objects.create(
                user=invoice.user,
                notification_type='system',
                priority='high',
                title='OVERDUE: Invoice Payment Required',
                message=f'Invoice {invoice.invoice_number} is {days_overdue} days overdue',
                link=f'/api/v1/invoices/{invoice.id}/'
            )
            
            sent_count += 1
            
        except Exception as e:
            print(f"Error sending overdue notice: {e}")
    
    return f"Sent {sent_count} invoice reminders"


@shared_task(name='apps.payments.tasks.check_expired_payment_methods')
def check_expired_payment_methods():
    """
    Check for expired payment methods and notify users
    Runs monthly on 1st at 8 AM
    """
    today = timezone.now()
    current_year = today.year
    current_month = today.month
    
    # Get expired payment methods
    expired_methods = PaymentMethod.objects.filter(
        is_active=True
    ).filter(
        models.Q(expiry_year__lt=current_year) |
        models.Q(expiry_year=current_year, expiry_month__lt=current_month)
    )
    
    notified_count = 0
    
    for method in expired_methods:
        try:
            send_mail(
                subject='Payment Method Expired - VetConnect',
                message=f"""
Hello {method.user.get_full_name()},

Your payment method has expired:

Card: {method.card_type} ending in {method.last_four}
Expired: {method.expiry_month:02d}/{method.expiry_year}

Please update your payment method to continue using VetConnect services.

Best regards,
VetConnect Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[method.user.email],
                fail_silently=True,
            )
            
            # Create notification
            Notification.objects.create(
                user=method.user,
                notification_type='system',
                priority='medium',
                title='Payment Method Expired',
                message=f'Your {method.card_type} ending in {method.last_four} has expired',
                link='/api/v1/payment-methods/'
            )
            
            # Deactivate expired method
            method.is_active = False
            method.save()
            
            notified_count += 1
            
        except Exception as e:
            print(f"Error notifying expired payment method: {e}")
    
    return f"Notified {notified_count} users about expired payment methods"


@shared_task
def process_pending_payments():
    """
    Check status of pending payments with Stripe
    """
    from .stripe_utils import StripePaymentService
    
    # Get payments that have been pending for more than 1 hour
    one_hour_ago = timezone.now() - timedelta(hours=1)
    pending_payments = Payment.objects.filter(
        status='pending',
        created_at__lt=one_hour_ago
    )
    
    stripe_service = StripePaymentService()
    verified_count = 0
    
    for payment in pending_payments[:50]:  # Process in batches
        try:
            stripe_service.verify_payment(payment)
            verified_count += 1
        except Exception as e:
            print(f"Error verifying payment {payment.id}: {e}")
    
    return f"Verified {verified_count} pending payments"


@shared_task
def send_payment_receipt(payment_id):
    """
    Send payment receipt via email
    """
    try:
        payment = Payment.objects.get(id=payment_id)
        
        send_mail(
            subject=f'Payment Receipt - {payment.transaction_id}',
            message=f"""
Hello {payment.user.get_full_name()},

Thank you for your payment.

Receipt Details:
Transaction ID: {payment.transaction_id}
Amount: {payment.currency} {payment.amount}
Payment Method: {payment.get_payment_method_display()}
Date: {payment.paid_at.strftime('%B %d, %Y at %I:%M %p')}

{f'Appointment: {payment.appointment.pet.name} with Dr. {payment.appointment.vet.get_full_name()}' if payment.appointment else ''}

This email serves as your receipt.

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[payment.user.email],
            fail_silently=False,
        )
        
        return f"Receipt sent for payment {payment_id}"
        
    except Payment.DoesNotExist:
        return f"Payment {payment_id} not found"
    except Exception as e:
        return f"Error sending receipt: {str(e)}"


@shared_task
def process_refund_request(refund_id):
    """
    Process refund request
    """
    try:
        from .stripe_utils import StripePaymentService
        
        refund = Refund.objects.get(id=refund_id)
        
        # Update status
        refund.status = 'processing'
        refund.save()
        
        # Process with Stripe
        stripe_service = StripePaymentService()
        updated_refund = stripe_service.process_refund(refund)
        
        # Notify user
        send_mail(
            subject='Refund Processed - VetConnect',
            message=f"""
Hello {refund.payment.user.get_full_name()},

Your refund has been processed.

Refund Details:
Amount: {refund.currency} {refund.amount}
Original Payment: {refund.payment.transaction_id}
Reason: {refund.get_reason_display()}

The refund will appear in your account within 5-10 business days.

Best regards,
VetConnect Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[refund.payment.user.email],
            fail_silently=False,
        )
        
        # Create notification
        Notification.objects.create(
            user=refund.payment.user,
            notification_type='system',
            priority='medium',
            title='Refund Processed',
            message=f'Your refund of {refund.currency} {refund.amount} has been processed',
            link=f'/api/v1/refunds/{refund.id}/'
        )
        
        return f"Refund {refund_id} processed successfully"
        
    except Refund.DoesNotExist:
        return f"Refund {refund_id} not found"
    except Exception as e:
        if 'refund' in locals():
            refund.status = 'failed'
            refund.description = str(e)
            refund.save()
        return f"Error processing refund: {str(e)}"


@shared_task
def generate_monthly_statement(user_id):
    """
    Generate monthly payment statement for user
    """
    try:
        from apps.accounts.models import User
        from django.db.models import Sum
        
        user = User.objects.get(id=user_id)
        
        # Get current month's payments
        today = timezone.now()
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        payments = Payment.objects.filter(
            user=user,
            created_at__gte=month_start,
            status='completed'
        )
        
        total_spent = payments.aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Build statement
        statement = f"""
Monthly Statement - {today.strftime('%B %Y')}
Account: {user.get_full_name()}

Summary:
Total Payments: {payments.count()}
Total Amount: {payments.first().currency if payments.exists() else 'USD'} {total_spent}

Transactions:
"""
        for payment in payments:
            statement += f"\n{payment.paid_at.strftime('%Y-%m-%d')}: {payment.currency} {payment.amount} - {payment.description}"
        
        # Send email
        send_mail(
            subject=f'Monthly Statement - {today.strftime("%B %Y")}',
            message=statement,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return f"Monthly statement sent to user {user_id}"
        
    except Exception as e:
        return f"Error generating statement: {str(e)}"