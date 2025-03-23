import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                           on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey('products.Product', verbose_name=_('product'),
                              on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('favorite')
        verbose_name_plural = _('favorites')
        ordering = ['-created_at']
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"
