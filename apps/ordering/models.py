import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')

    class PaymentMethodChoices(models.TextChoices):
        CASH = 'cash', _('Cash on delivery')
        CARD = 'card', _('Credit card')
        TRANSFER = 'transfer', _('Bank transfer')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                           on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(_('status'), max_length=20,
                            choices=StatusChoices.choices,
                            default=StatusChoices.PENDING)
    total_amount = models.DecimalField(_('total amount'), max_digits=10,
                                     decimal_places=2,
                                     validators=[MinValueValidator(0)])
    shipping_address = models.TextField(_('shipping address'))
    payment_method = models.CharField(_('payment method'), max_length=20,
                                   choices=PaymentMethodChoices.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.user.email}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, verbose_name=_('order'),
                            on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', verbose_name=_('product'),
                              on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(_('quantity'),
                                         validators=[MinValueValidator(1)])
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2,
                              validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = _('order item')
        verbose_name_plural = _('order items')

    def __str__(self):
        return f"{self.order.id} - {self.product.name} ({self.quantity})"

    @property
    def total_price(self):
        return self.quantity * self.price
