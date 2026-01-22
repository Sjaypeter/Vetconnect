from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment, Wallet
from apps.accounts.models import User
from apps.notifications.models import Notification


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create wallet for new users"""
    if created:
        Wallet.objects.get_or_create(user=instance)


@receiver(post_save, sender=Payment)
def notify_payment_status(sender, instance, created, **kwargs):
    """Send notification when payment status changes"""
    if not created and instance.status == 'completed':
        Notification.objects.create(
            user=instance.user,
            notification_type='system',
            priority='medium',
            title='Payment Successful',
            message=f'Your payment of ${instance.amount} has been processed successfully',
            link=f'/api/v1/payments/{instance.id}/'
        )