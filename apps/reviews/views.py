from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Avg, Count
from .models import Review, ReviewHelpful
from .serializers import ReviewSerializer, ReviewCreateSerializer, ReviewStatsSerializer
from apps.notifications.models import Notification


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for reviews and ratings
    
    list: Get all reviews (filtered by user type)
    create: Create new review (client only, after completed appointment)
    retrieve: Get specific review
    update: Update review (own reviews only)
    destroy: Delete review (own reviews only)
    by_vet: Get reviews for specific vet
    stats: Get review statistics
    my_reviews: Get current user's reviews
    mark_helpful: Mark review as helpful
    """
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['vet', 'rating', 'would_recommend', 'is_approved']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']
    
    def get_queryset(self):
        """Filter reviews based on user type"""
        user = self.request.user
        
        if user.user_type == 'client':
            # Clients see their own reviews and all approved reviews
            from django.db.models import Q
            return Review.objects.filter(
                Q(client=user) | Q(is_approved=True)
            ).distinct()
        elif user.user_type == 'vet':
            # Vets see reviews about them
            return Review.objects.filter(vet=user, is_approved=True)
        
        return Review.objects.filter(is_approved=True)
    
    def get_serializer_class(self):
        """Use different serializer for create action"""
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def perform_create(self, serializer):
        """Create review and notify vet"""
        # Validate user is client
        if self.request.user.user_type != 'client':
            raise PermissionError('Only clients can create reviews')
        
        review = serializer.save(client=self.request.user)
        
        # Notify vet
        Notification.objects.create(
            user=review.vet,
            notification_type='review',
            title='New Review',
            message=f'{self.request.user.get_full_name()} left you a {review.rating}-star review',
            link=f'/api/v1/reviews/{review.id}/',
            priority='medium'
        )
        
        # Update vet's average rating
        if hasattr(review.vet, 'vet_profile'):
            review.vet.vet_profile.update_rating()
    
    def perform_update(self, serializer):
        """Only allow users to update their own reviews"""
        review = self.get_object()
        if review.client != self.request.user:
            raise PermissionError('You can only update your own reviews')
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only allow users to delete their own reviews"""
        if instance.client != self.request.user:
            raise PermissionError('You can only delete your own reviews')
        instance.delete()
    
    @swagger_auto_schema(
        operation_description="Get reviews for a specific veterinarian",
        manual_parameters=[
            openapi.Parameter(
                'vet_id',
                openapi.IN_QUERY,
                description="Veterinarian ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def by_vet(self, request):
        """Get all reviews for a specific vet"""
        vet_id = request.query_params.get('vet_id')
        
        if not vet_id:
            return Response(
                {'error': 'vet_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reviews = self.get_queryset().filter(
            vet_id=vet_id,
            is_approved=True
        ).order_by('-created_at')
        
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Get review statistics for a veterinarian",
        manual_parameters=[
            openapi.Parameter(
                'vet_id',
                openapi.IN_QUERY,
                description="Veterinarian ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: ReviewStatsSerializer}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get review statistics for a vet"""
        vet_id = request.query_params.get('vet_id')
        
        if not vet_id:
            return Response(
                {'error': 'vet_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reviews = Review.objects.filter(vet_id=vet_id, is_approved=True)
        
        stats = {
            'total_reviews': reviews.count(),
            'average_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'rating_distribution': {
                '5': reviews.filter(rating=5).count(),
                '4': reviews.filter(rating=4).count(),
                '3': reviews.filter(rating=3).count(),
                '2': reviews.filter(rating=2).count(),
                '1': reviews.filter(rating=1).count(),
            },
            'would_recommend_percentage': 0,
            'average_communication': reviews.aggregate(
                Avg('communication_rating')
            )['communication_rating__avg'] or 0,
            'average_professionalism': reviews.aggregate(
                Avg('professionalism_rating')
            )['professionalism_rating__avg'] or 0,
            'average_care_quality': reviews.aggregate(
                Avg('care_quality_rating')
            )['care_quality_rating__avg'] or 0,
        }
        
        # Calculate recommendation percentage
        total = stats['total_reviews']
        if total > 0:
            recommend_count = reviews.filter(would_recommend=True).count()
            stats['would_recommend_percentage'] = round((recommend_count / total) * 100, 2)
        
        serializer = ReviewStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get current user's reviews"""
        if request.user.user_type != 'client':
            return Response(
                {'error': 'Only clients have reviews'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reviews = Review.objects.filter(client=request.user)
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Mark a review as helpful",
        responses={200: 'Review marked as helpful'}
    )
    @action(detail=True, methods=['post'])
    def mark_helpful(self, request, pk=None):
        """Mark a review as helpful"""
        review = self.get_object()
        
        # Check if already marked
        helpful, created = ReviewHelpful.objects.get_or_create(
            review=review,
            user=request.user
        )
        
        if created:
            return Response({
                'message': 'Review marked as helpful',
                'helpful_count': review.helpful_votes.count()
            })
        else:
            return Response({
                'message': 'You already marked this review as helpful',
                'helpful_count': review.helpful_votes.count()
            })
    
    @swagger_auto_schema(
        operation_description="Remove helpful mark from review",
        responses={200: 'Helpful mark removed'}
    )
    @action(detail=True, methods=['post'])
    def unmark_helpful(self, request, pk=None):
        """Remove helpful mark from review"""
        review = self.get_object()
        
        deleted = ReviewHelpful.objects.filter(
            review=review,
            user=request.user
        ).delete()
        
        if deleted[0] > 0:
            return Response({
                'message': 'Helpful mark removed',
                'helpful_count': review.helpful_votes.count()
            })
        else:
            return Response({
                'message': 'You have not marked this review as helpful',
                'helpful_count': review.helpful_votes.count()
            })
    
    @swagger_auto_schema(
        operation_description="Add vet response to review",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['response'],
            properties={
                'response': openapi.Schema(type=openapi.TYPE_STRING)
            }
        )
    )
    @action(detail=True, methods=['post'])
    def add_response(self, request, pk=None):
        """Add vet's response to a review"""
        review = self.get_object()
        
        # Only the reviewed vet can respond
        if request.user != review.vet:
            return Response(
                {'error': 'Only the reviewed vet can respond'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        response_text = request.data.get('response')
        if not response_text:
            return Response(
                {'error': 'Response text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        review.vet_response = response_text
        review.vet_response_date = timezone.now()
        review.save()
        
        # Notify client
        Notification.objects.create(
            user=review.client,
            notification_type='review',
            title='Vet Responded to Your Review',
            message=f'Dr. {review.vet.get_full_name()} responded to your review',
            link=f'/api/v1/reviews/{review.id}/',
            priority='low'
        )
        
        serializer = self.get_serializer(review)
        return Response(serializer.data)