from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta, date
from apps.appointments.models import Appointment
from apps.payments.models import Payment
from apps.accounts.models import User
from apps.reviews.models import Review

@shared_task(name='apps.analytics.tasks.generate_daily_statistics')
def generate_daily_statistics():
    """
    Generate daily statistics for the platform
    Runs daily at 12:05 AM
    """
    
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Appointment statistics
    appointments_stats = {
        'total': Appointment.objects.filter(
            created_at__date=yesterday
        ).count(),
        'completed': Appointment.objects.filter(
            appointment_date__date=yesterday,
            status='completed'
        ).count(),
        'cancelled': Appointment.objects.filter(
            appointment_date__date=yesterday,
            status='cancelled'
        ).count(),
    }
    
    # Payment statistics
    payments = Payment.objects.filter(
        paid_at__date=yesterday,
        status='completed'
    )
    payments_stats = {
        'count': payments.count(),
        'total_amount': payments.aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    # User statistics
    users_stats = {
        'new_clients': User.objects.filter(
            date_joined__date=yesterday,
            user_type='client'
        ).count(),
        'new_vets': User.objects.filter(
            date_joined__date=yesterday,
            user_type='vet'
        ).count(),
    }
    
    # Review statistics
    reviews_stats = {
        'count': Review.objects.filter(
            created_at__date=yesterday
        ).count(),
        'average_rating': Review.objects.filter(
            created_at__date=yesterday
        ).aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    # Log statistics (you can save to database if needed)
    stats = {
        'date': yesterday,
        'appointments': appointments_stats,
        'payments': payments_stats,
        'users': users_stats,
        'reviews': reviews_stats,
    }
    
    print(f"Daily statistics generated for {yesterday}: {stats}")
    
    return f"Statistics generated for {yesterday}"


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