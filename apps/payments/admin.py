from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Payment, Invoice, InvoiceItem, Refund,
    PaymentMethod, Wallet, WalletTransaction
)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id', 'user', 'amount', 'currency',
        'payment_method', 'status_badge', 'paid_at', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'currency', 'created_at', 'paid_at']
    search_fields = [
        'transaction_id', 'user__username', 'user__email',
        'stripe_payment_intent_id', 'description'
    ]
    readonly_fields = [
        'transaction_id', 'stripe_payment_intent_id',
        'stripe_charge_id', 'stripe_customer_id',
        'paid_at', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'appointment', 'transaction_id')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'payment_method', 'status', 'description')
        }),
        ('Stripe Information', {
            'fields': (
                'stripe_payment_intent_id', 'stripe_charge_id',
                'stripe_customer_id'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('paid_at', 'created_at', 'updated_at')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'processing': 'blue',
            'failed': 'red',
            'refunded': 'gray',
            'cancelled': 'darkgray'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['description', 'quantity', 'unit_price', 'amount']
    readonly_fields = ['amount']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'user', 'total', 'currency',
        'status_badge', 'issue_date', 'due_date', 'paid_date'
    ]
    list_filter = ['status', 'currency', 'issue_date', 'due_date']
    search_fields = ['invoice_number', 'user__username', 'user__email']
    readonly_fields = [
        'invoice_number', 'tax_amount', 'total',
        'paid_date', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'issue_date'
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_number', 'user', 'appointment', 'payment', 'status')
        }),
        ('Amounts', {
            'fields': (
                'subtotal', 'tax_rate', 'tax_amount',
                'discount_amount', 'total', 'currency'
            )
        }),
        ('Dates', {
            'fields': ('issue_date', 'due_date', 'paid_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'paid': 'green',
            'sent': 'blue',
            'overdue': 'red',
            'draft': 'gray',
            'cancelled': 'darkgray'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payment', 'amount', 'currency',
        'reason', 'status_badge', 'initiated_by', 'created_at'
    ]
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['payment__transaction_id', 'stripe_refund_id', 'description']
    readonly_fields = ['stripe_refund_id', 'processed_at', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('payment', 'amount', 'currency', 'reason', 'description')
        }),
        ('Status', {
            'fields': ('status', 'initiated_by', 'processed_at')
        }),
        ('Stripe', {
            'fields': ('stripe_refund_id',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'processing': 'blue',
            'failed': 'red',
            'cancelled': 'gray'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'card_type', 'masked_number',
        'expiry', 'is_default', 'is_active', 'created_at'
    ]
    list_filter = ['card_type', 'is_default', 'is_active', 'created_at']
    search_fields = ['user__username', 'user__email', 'last_four', 'cardholder_name']
    readonly_fields = ['stripe_payment_method_id', 'stripe_customer_id', 'created_at', 'updated_at']
    
    def masked_number(self, obj):
        return f"****{obj.last_four}"
    masked_number.short_description = 'Card Number'
    
    def expiry(self, obj):
        return f"{obj.expiry_month:02d}/{obj.expiry_year}"
    expiry.short_description = 'Expiry'


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'currency', 'is_active', 'updated_at']
    list_filter = ['is_active', 'currency']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'wallet', 'transaction_type', 'amount',
        'balance_before', 'balance_after', 'created_at'
    ]
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['wallet__user__username', 'description', 'reference']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'