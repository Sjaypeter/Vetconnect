from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import (
    Payment, Invoice, InvoiceItem, Refund,
    PaymentMethod, Wallet, WalletTransaction
)
from .serializers import (
    PaymentSerializer, PaymentCreateSerializer,
    InvoiceSerializer, InvoiceCreateSerializer, InvoiceItemSerializer,
    RefundSerializer, RefundCreateSerializer,
    PaymentMethodSerializer, PaymentMethodCreateSerializer,
    WalletSerializer, WalletTransactionSerializer, WalletTopUpSerializer,
    PaymentStatsSerializer
)
from .stripe_utils import StripePaymentService


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payment management
    
    list: Get all payments for current user
    create: Create a new payment
    retrieve: Get payment details
    stats: Get payment statistics
    verify: Verify payment status with Stripe
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'appointment']
    search_fields = ['transaction_id', 'description']
    ordering_fields = ['created_at', 'amount', 'paid_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Only show user's own payments"""
        return Payment.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    @swagger_auto_schema(
        operation_description="Create a new payment",
        request_body=PaymentCreateSerializer,
        responses={201: PaymentSerializer}
    )
    def create(self, request):
        """Create a new payment using Stripe"""
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Initialize Stripe service
        stripe_service = StripePaymentService()
        
        try:
            # Create payment
            payment = stripe_service.create_payment(
                user=request.user,
                amount=serializer.validated_data['amount'],
                appointment_id=serializer.validated_data.get('appointment_id'),
                payment_method_id=serializer.validated_data.get('payment_method_id'),
                description=serializer.validated_data.get('description', ''),
                save_payment_method=serializer.validated_data.get('save_payment_method', False)
            )
            
            result_serializer = PaymentSerializer(payment)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        operation_description="Get payment statistics",
        responses={200: PaymentStatsSerializer}
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get payment statistics for current user"""
        payments = self.get_queryset()
        
        stats = {
            'total_payments': payments.count(),
            'total_amount': payments.filter(
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'completed_payments': payments.filter(status='completed').count(),
            'pending_payments': payments.filter(status='pending').count(),
            'failed_payments': payments.filter(status='failed').count(),
            'refunded_amount': Refund.objects.filter(
                payment__user=request.user,
                status='completed'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'currency': 'USD'
        }
        
        serializer = PaymentStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Verify payment status with Stripe"
    )
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify payment status with Stripe"""
        payment = self.get_object()
        stripe_service = StripePaymentService()
        
        try:
            updated_payment = stripe_service.verify_payment(payment)
            serializer = self.get_serializer(updated_payment)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for invoice management
    
    list: Get all invoices
    create: Create new invoice
    retrieve: Get invoice details
    send: Send invoice via email
    mark_paid: Mark invoice as paid
    download: Download invoice PDF
    """
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'appointment']
    ordering_fields = ['created_at', 'due_date', 'total']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter invoices based on user type"""
        user = self.request.user
        if user.user_type == 'client':
            return Invoice.objects.filter(user=user)
        elif user.user_type == 'vet':
            # Vets can see invoices for their appointments
            return Invoice.objects.filter(appointment__vet=user)
        return Invoice.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer
    
    def create(self, request):
        """Create new invoice"""
        if request.user.user_type != 'vet':
            return Response(
                {'error': 'Only vets can create invoices'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate invoice number
        import uuid
        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        # Calculate subtotal
        subtotal = sum(
            item['quantity'] * item['unit_price']
            for item in serializer.validated_data['items']
        )
        
        # Create invoice
        invoice = Invoice.objects.create(
            invoice_number=invoice_number,
            user=request.user,
            appointment_id=serializer.validated_data.get('appointment_id'),
            subtotal=subtotal,
            tax_rate=serializer.validated_data['tax_rate'],
            discount_amount=serializer.validated_data['discount_amount'],
            due_date=serializer.validated_data['due_date'],
            notes=serializer.validated_data.get('notes', ''),
            terms=serializer.validated_data.get('terms', '')
        )
        
        # Create invoice items
        for item_data in serializer.validated_data['items']:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
        
        # Calculate total
        invoice.calculate_total()
        
        result_serializer = InvoiceSerializer(invoice)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send invoice via email"""
        invoice = self.get_object()
        
        # TODO: Implement email sending
        invoice.status = 'sent'
        invoice.save()
        
        return Response({'message': 'Invoice sent successfully'})
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid"""
        invoice = self.get_object()
        
        if invoice.status == 'paid':
            return Response(
                {'error': 'Invoice is already paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.mark_as_paid()
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class RefundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for refund management
    
    list: Get all refunds
    create: Create refund request
    retrieve: Get refund details
    approve: Approve refund (admin only)
    """
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'reason']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Only show user's own refunds"""
        return Refund.objects.filter(payment__user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RefundCreateSerializer
        return RefundSerializer
    
    def create(self, request):
        """Create refund request"""
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment = Payment.objects.get(
            id=serializer.validated_data['payment_id'],
            user=request.user
        )
        
        # Check if payment can be refunded
        if payment.status != 'completed':
            return Response(
                {'error': 'Only completed payments can be refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already refunded
        if payment.status == 'refunded':
            return Response(
                {'error': 'Payment has already been refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get refund amount (full or partial)
        refund_amount = serializer.validated_data.get('amount', payment.amount)
        
        if refund_amount > payment.amount:
            return Response(
                {'error': 'Refund amount cannot exceed payment amount'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create refund
        refund = Refund.objects.create(
            payment=payment,
            amount=refund_amount,
            currency=payment.currency,
            reason=serializer.validated_data['reason'],
            description=serializer.validated_data.get('description', ''),
            initiated_by=request.user,
            status='pending'
        )
        
        result_serializer = RefundSerializer(refund)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve refund and process with Stripe"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admins can approve refunds'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        refund = self.get_object()
        
        if refund.status != 'pending':
            return Response(
                {'error': f'Cannot approve refund with status: {refund.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stripe_service = StripePaymentService()
        
        try:
            updated_refund = stripe_service.process_refund(refund)
            serializer = self.get_serializer(updated_refund)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payment method management
    
    list: Get all payment methods
    create: Add new payment method
    retrieve: Get payment method details
    destroy: Remove payment method
    set_default: Set as default payment method
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only show user's own payment methods"""
        return PaymentMethod.objects.filter(user=self.request.user, is_active=True)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentMethodCreateSerializer
        return PaymentMethodSerializer
    
    def create(self, request):
        """Add new payment method"""
        serializer = PaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        stripe_service = StripePaymentService()
        
        try:
            payment_method = stripe_service.add_payment_method(
                user=request.user,
                stripe_payment_method_id=serializer.validated_data['stripe_payment_method_id'],
                is_default=serializer.validated_data.get('is_default', False)
            )
            
            result_serializer = PaymentMethodSerializer(payment_method)
            return Response(result_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, pk=None):
        """Remove payment method"""
        payment_method = self.get_object()
        
        stripe_service = StripePaymentService()
        
        try:
            stripe_service.remove_payment_method(payment_method)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default"""
        payment_method = self.get_object()
        payment_method.is_default = True
        payment_method.save()
        
        serializer = self.get_serializer(payment_method)
        return Response(serializer.data)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for wallet management
    
    retrieve: Get wallet details
    transactions: Get wallet transactions
    top_up: Add funds to wallet
    """
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only show user's own wallet"""
        return Wallet.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create user's wallet"""
        wallet, created = Wallet.objects.get_or_create(user=self.request.user)
        return wallet
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get wallet transactions"""
        wallet = self.get_object()
        transactions = wallet.transactions.all()
        serializer = WalletTransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        request_body=WalletTopUpSerializer,
        responses={200: WalletSerializer}
    )
    @action(detail=False, methods=['post'])
    def top_up(self, request):
        """Add funds to wallet"""
        serializer = WalletTopUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wallet = self.get_object()
        amount = serializer.validated_data['amount']
        
        # TODO: Process payment with Stripe
        
        # Add funds
        balance_before = wallet.balance
        wallet.add_funds(amount)
        
        # Create transaction record
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='credit',
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            description='Wallet top-up',
            reference=f'TOPUP-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        )
        
        result_serializer = WalletSerializer(wallet)
        return Response(result_serializer.data)