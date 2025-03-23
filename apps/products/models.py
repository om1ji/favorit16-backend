import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=100)
    logo = models.ImageField(_('logo'), upload_to='brands/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('brand')
        verbose_name_plural = _('brands')
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255)
    image = models.ImageField(_('image'), upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey('self', verbose_name=_('parent category'),
                             on_delete=models.CASCADE, null=True, blank=True,
                             related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(_('image'), upload_to='products/')
    alt_text = models.CharField(_('alternative text'), max_length=255, blank=True)
    is_feature = models.BooleanField(_('feature image'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('product image')
        verbose_name_plural = _('product images')

    def __str__(self):
        return f"Image {self.id}"


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255)
    description = models.TextField(_('description'))
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2,
                              validators=[MinValueValidator(0)])
    old_price = models.DecimalField(_('old price'), max_digits=10, decimal_places=2,
                                  validators=[MinValueValidator(0)], null=True, blank=True)
    category = models.ForeignKey(Category, verbose_name=_('category'),
                               on_delete=models.CASCADE, related_name='products')
    images = models.ManyToManyField(ProductImage, verbose_name=_('images'),
                                  related_name='products')
    in_stock = models.BooleanField(_('in stock'), default=True)
    quantity = models.PositiveIntegerField(_('quantity'), default=0)
    
    # Tire specific fields
    brand = models.ForeignKey(Brand, verbose_name=_('brand'), 
                            on_delete=models.SET_NULL, null=True, blank=True,
                            related_name='products')
    diameter = models.PositiveSmallIntegerField(_('diameter'), null=True, blank=True,
                                             help_text=_('Rim diameter in inches'))
    width = models.DecimalField(_('width'), max_digits=4, decimal_places=1,
                             null=True, blank=True, 
                             help_text=_('Tire width in millimeters'))
    profile = models.PositiveSmallIntegerField(_('profile'), null=True, blank=True,
                                           help_text=_('Tire profile height as percentage of width'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def set_feature_image(self, image):
        """Set the feature image for the product."""
        # Remove feature flag from all other images
        self.images.filter(is_feature=True).update(is_feature=False)
        # Set the new feature image
        if isinstance(image, ProductImage):
            image.is_feature = True
            image.save()
        elif isinstance(image, str):
            try:
                image = self.images.get(id=image)
                image.is_feature = True
                image.save()
            except ProductImage.DoesNotExist:
                pass

    @property
    def feature_image(self):
        """Get the feature image for the product."""
        return self.images.filter(is_feature=True).first()

    @property
    def is_available(self):
        return self.in_stock and self.quantity > 0

    @property
    def has_discount(self):
        return bool(self.old_price and self.old_price > self.price)

    @property
    def discount_percentage(self):
        if self.has_discount:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0
