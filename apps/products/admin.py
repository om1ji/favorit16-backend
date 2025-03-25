from django.contrib import admin
from .models import Category, Product, ProductImage, Brand


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'alt_text', 'is_feature', 'created_at')
    list_filter = ('is_feature', 'created_at')
    search_fields = ('alt_text', 'product__name')
    ordering = ('-created_at',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price', 'old_price', 'diameter', 'width', 'profile', 'in_stock', 'quantity', 'created_at')
    list_filter = ('category', 'brand', 'in_stock', 'diameter', 'created_at')
    search_fields = ('name', 'description', 'brand__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {
            'fields': ('category', 'brand', 'name', 'description')
        }),
        ('Tire Specifications', {
            'fields': ('diameter', 'width', 'profile')
        }),
        ('Pricing', {
            'fields': ('price', 'old_price')
        }),
        ('Stock', {
            'fields': ('in_stock', 'quantity')
        }),
        ('Dates', {
            'fields': ('created_at',)
        }),
    )
    
    readonly_fields = ('created_at',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name',)
    ordering = ('name',)
