from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'shipping_address')
    ordering = ('-created_at',)
    inlines = [OrderItemInline]
    
    readonly_fields = ('total_amount', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'payment_method')
        }),
        ('Shipping Information', {
            'fields': ('shipping_address',)
        }),
        ('Order Details', {
            'fields': ('total_amount', 'created_at')
        }),
    )
