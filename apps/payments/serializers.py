from rest_framework import serializers
from .models import (
    Payment, Invoice, InvoiceItem, Refund,
    PaymentMethod, Wallet, WalletTransaction
)


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    appointment_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_name', 'appointment', 'appointment_details',
            'amount', 'currency', 'payment_method', 'status',
            'transaction_id', 'description', 'metadata',
            'paid_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'user', 'transaction_id', 'stripe_payment_intent_id',
            'stripe_charge_id', 'paid_at', 'created_at', 'updated_at'
        ]
    
    def get_appointment_details(self, obj):
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'date': obj.appointment.appointment_date,
                'pet_name': obj.appointment.pet.name,
                'vet_name': obj.appointment.vet.get_full_name()
            }
        return None


class PaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating payments"""
    appointment_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=Payment.PAYMENT_METHOD_CHOICES)
    payment_method_id = serializers.CharField(required=False, help_text="Stripe payment method ID")
    description = serializers.CharField(required=False, allow_blank=True)
    save_payment_method = serializers.BooleanField(default=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value


class InvoiceItemSerializer(serializers.ModelSerializer):
    """Serializer for Invoice Items"""
    
    class Meta:
        model = InvoiceItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'amount']
        read_only_fields = ['amount']


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model"""
    items = InvoiceItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payment_status = serializers.CharField(source='payment.status', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'user', 'user_name', 'appointment',
            'payment', 'payment_status', 'status', 'subtotal', 'tax_rate',
            'tax_amount', 'discount_amount', 'total', 'currency',
            'issue_date', 'due_date', 'paid_date', 'notes', 'terms',
            'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'invoice_number', 'tax_amount', 'total',
            'paid_date', 'created_at', 'updated_at'
        ]


class InvoiceCreateSerializer(serializers.Serializer):
    """Serializer for creating invoices"""
    appointment_id = serializers.IntegerField(required=False)
    items = InvoiceItemSerializer(many=True)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    due_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    terms = serializers.CharField(required=False, allow_blank=True)


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for Refund model"""
    payment_details = serializers.SerializerMethodField()
    initiated_by_name = serializers.CharField(source='initiated_by.get_full_name', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_details', 'amount', 'currency',
            'reason', 'description', 'status', 'initiated_by',
            'initiated_by_name', 'processed_at', 'created_at'
        ]
        read_only_fields = [
            'stripe_refund_id', 'processed_at', 'created_at'
        ]
    
    def get_payment_details(self, obj):
        return {
            'transaction_id': obj.payment.transaction_id,
            'amount': obj.payment.amount,
            'status': obj.payment.status
        }


class RefundCreateSerializer(serializers.Serializer):
    """Serializer for creating refunds"""
    payment_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    reason = serializers.ChoiceField(choices=Refund.REFUND_REASON_CHOICES)
    description = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value and value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than zero")
        return value


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for Payment Method model"""
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'card_type', 'last_four', 'expiry_month', 'expiry_year',
            'cardholder_name', 'is_default', 'is_active', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'stripe_payment_method_id', 'stripe_customer_id',
            'created_at', 'updated_at'
        ]
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return (obj.expiry_year < now.year or 
                (obj.expiry_year == now.year and obj.expiry_month < now.month))


class PaymentMethodCreateSerializer(serializers.Serializer):
    """Serializer for adding payment methods"""
    stripe_payment_method_id = serializers.CharField()
    is_default = serializers.BooleanField(default=False)


class WalletSerializer(serializers.ModelSerializer):
    """Serializer for Wallet model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'user_name', 'balance', 'currency',
            'is_active', 'recent_transactions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'balance', 'created_at', 'updated_at']
    
    def get_recent_transactions(self, obj):
        transactions = obj.transactions.all()[:5]
        return WalletTransactionSerializer(transactions, many=True).data


class WalletTransactionSerializer(serializers.ModelSerializer):
    """Serializer for Wallet Transaction model"""
    
    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'balance_before',
            'balance_after', 'description', 'reference', 'created_at'
        ]
        read_only_fields = ['created_at']


class WalletTopUpSerializer(serializers.Serializer):
    """Serializer for wallet top-up"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method_id = serializers.CharField(required=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        if value > 10000:
            raise serializers.ValidationError("Maximum top-up amount is 10,000")
        return value


class PaymentStatsSerializer(serializers.Serializer):
    """Serializer for payment statistics"""
    total_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    completed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    refunded_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()