from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta, date
from apps.appointments.models import Appointment
from apps.payments.models import Payment
from apps.accounts.models import User
from apps.reviews.models import Review
from .models import DailyStatistic



@shared_task(name='apps.analytics.tasks.generate_daily_statistics')
def generate_daily_statistics():
    
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Create or update statistics
    stats, created = DailyStatistic.objects.get_or_create(
        date=yesterday,
        defaults={
            'total_users': User.objects.count(),
            'new_users_today': User.objects.filter(date_joined__date=yesterday).count(),
            'total_appointments': Appointment.objects.filter(created_at__date=yesterday).count(),
            'completed_appointments': Appointment.objects.filter(
                appointment_date__date=yesterday,
                status='completed'
            ).count(),
            'cancelled_appointments': Appointment.objects.filter(
                appointment_date__date=yesterday,
                status='cancelled'
            ).count(),
            'number_of_payments': Payment.objects.filter(paid_at__date=yesterday).count(),
            'total_revenue': Payment.objects.filter(
                paid_at__date=yesterday,
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_reviews': Review.objects.filter(created_at__date=yesterday).count(),
            'average_rating': Review.objects.filter(
                created_at__date=yesterday
            ).aggregate(Avg('rating'))['rating__avg'] or 0,
        }
    )
    
    return f"Statistics saved for {yesterday}"




@shared_task
def generate_vet_performance_report(vet_id):
    """
    Generate performance report for a veterinarian
    """
    from apps.accounts.models import User
    from apps.appointments.models import Appointment
    from apps.reviews.models import Review
    
    try:
        vet = User.objects.get(id=vet_id, user_type='vet')
        
        # Get last 30 days data
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        appointments = Appointment.objects.filter(
            vet=vet,
            appointment_date__gte=thirty_days_ago
        )
        
        reviews = Review.objects.filter(
            vet=vet,
            created_at__gte=thirty_days_ago
        )
        
        report = {
            'vet_name': vet.get_full_name(),
            'period': '30 days',
            'total_appointments': appointments.count(),
            'completed_appointments': appointments.filter(status='completed').count(),
            'cancelled_appointments': appointments.filter(status='cancelled').count(),
            'no_show_appointments': appointments.filter(status='no_show').count(),
            'average_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'total_reviews': reviews.count(),
        }
        
        print(f"Performance report for {vet.get_full_name()}: {report}")
        
        return f"Report generated for vet {vet_id}"
        
    except User.DoesNotExist:
        return f"Vet {vet_id} not found"
    except Exception as e:
        return f"Error generating report: {str(e)}"


@shared_task
def calculate_revenue_metrics():
    """
    Calculate revenue metrics for the platform
    """
    from apps.payments.models import Payment
    
    # This month
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    this_month_payments = Payment.objects.filter(
        paid_at__gte=month_start,
        status='completed'
    )
    
    # Last month
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(seconds=1)
    
    last_month_payments = Payment.objects.filter(
        paid_at__gte=last_month_start,
        paid_at__lte=last_month_end,
        status='completed'
    )
    
    metrics = {
        'this_month': {
            'count': this_month_payments.count(),
            'revenue': this_month_payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        },
        'last_month': {
            'count': last_month_payments.count(),
            'revenue': last_month_payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        }
    }
    
    # Calculate growth
    if metrics['last_month']['revenue'] > 0:
        metrics['growth'] = (
            (metrics['this_month']['revenue'] - metrics['last_month']['revenue']) 
            / metrics['last_month']['revenue'] * 100
        )
    else:
        metrics['growth'] = 0
    
    print(f"Revenue metrics: {metrics}")
    
    return f"Revenue metrics calculated: {metrics}"