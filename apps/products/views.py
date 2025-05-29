from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db import models
from django_filters import rest_framework as filters
from rest_framework import generics, permissions
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Category, Product, Brand
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    BrandSerializer,
)


class CategoryFilter(filters.FilterSet):
    class Meta:
        model = Category
        fields = {
            'parent': ['exact', 'isnull'],
        }


class ProductFilter(filters.FilterSet):
    # Общие фильтры
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = filters.UUIDFilter(field_name='category__id')
    brand = filters.UUIDFilter(field_name='brand__id')
    diameter = filters.NumberFilter(field_name='diameter', lookup_expr='exact')
    min_diameter = filters.NumberFilter(field_name='diameter', lookup_expr='gte')
    max_diameter = filters.NumberFilter(field_name='diameter', lookup_expr='lte')
    is_available = filters.BooleanFilter(method='filter_is_available')
    has_discount = filters.BooleanFilter(method='filter_has_discount')
    
    # Фильтры для шин
    width = filters.NumberFilter(field_name='width', lookup_expr='exact')
    min_width = filters.NumberFilter(field_name='width', lookup_expr='gte')
    max_width = filters.NumberFilter(field_name='width', lookup_expr='lte')
    profile = filters.NumberFilter(field_name='profile', lookup_expr='exact')
    min_profile = filters.NumberFilter(field_name='profile', lookup_expr='gte')
    max_profile = filters.NumberFilter(field_name='profile', lookup_expr='lte')
    
    # Фильтры для дисков
    wheel_width = filters.NumberFilter(field_name='wheel_width', lookup_expr='exact')
    min_wheel_width = filters.NumberFilter(field_name='wheel_width', lookup_expr='gte')
    max_wheel_width = filters.NumberFilter(field_name='wheel_width', lookup_expr='lte')
    et_offset = filters.NumberFilter(field_name='et_offset', lookup_expr='exact')
    min_et_offset = filters.NumberFilter(field_name='et_offset', lookup_expr='gte')
    max_et_offset = filters.NumberFilter(field_name='et_offset', lookup_expr='lte')
    pcd = filters.NumberFilter(field_name='pcd', lookup_expr='exact')
    min_pcd = filters.NumberFilter(field_name='pcd', lookup_expr='gte')
    max_pcd = filters.NumberFilter(field_name='pcd', lookup_expr='lte')
    bolt_count = filters.NumberFilter(field_name='bolt_count', lookup_expr='exact')
    center_bore = filters.NumberFilter(field_name='center_bore', lookup_expr='exact')
    min_center_bore = filters.NumberFilter(field_name='center_bore', lookup_expr='gte')
    max_center_bore = filters.NumberFilter(field_name='center_bore', lookup_expr='lte')

    class Meta:
        model = Product
        fields = {
            'in_stock': ['exact'],
            'category': ['exact'],
            'brand': ['exact'],
            'diameter': ['exact', 'in'],
            # Поля для шин
            'width': ['exact'],
            'profile': ['exact'],
            # Поля для дисков
            'wheel_width': ['exact'],
            'et_offset': ['exact'],
            'pcd': ['exact'],
            'bolt_count': ['exact'],
            'center_bore': ['exact'],
        }

    def filter_is_available(self, queryset, name, value):
        if value:
            return queryset.filter(in_stock=True, quantity__gt=0)
        return queryset

    def filter_has_discount(self, queryset, name, value):
        if value:
            return queryset.exclude(old_price__isnull=True).filter(old_price__gt=models.F('price'))
        return queryset


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)
    filterset_class = CategoryFilter

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'id'

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.select_related('category').all()
    serializer_class = BrandSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [filters.DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Если в URL есть category_id, фильтруем по нему
        category_id = self.kwargs.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        return queryset

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class BrandDetailView(generics.RetrieveAPIView):
    queryset = Brand.objects.select_related('category').all()
    serializer_class = BrandSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'id'

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.select_related('category', 'brand').prefetch_related('images')
    serializer_class = ProductListSerializer
    permission_classes = (permissions.AllowAny,)
    filterset_class = ProductFilter
    filter_backends = [filters.DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'category__name', 'brand__name']
    ordering_fields = [
        'price', 'created_at', 'name', 
        # Общие поля
        'diameter',
        # Поля для шин
        'width', 'profile',
        # Поля для дисков
        'wheel_width', 'et_offset', 'pcd', 'bolt_count', 'center_bore'
    ]
    ordering = ['-created_at']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.select_related('category', 'brand').prefetch_related('images')
    serializer_class = ProductDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
