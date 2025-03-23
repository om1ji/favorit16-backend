import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                           on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey('products.Product', verbose_name=_('product'),
                              on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_('quantity'),
                                         validators=[MinValueValidator(1)],
                                         default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('cart item')
        verbose_name_plural = _('cart items')
        ordering = ['-created_at']
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.quantity})"

    @property
    def total_price(self):
        return self.quantity * self.product.price

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity > self.product.quantity:
            raise ValidationError({
                'quantity': _('Requested quantity is not available.')
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
