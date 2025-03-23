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
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = filters.UUIDFilter(field_name='category__id')
    brand = filters.UUIDFilter(field_name='brand__id')
    diameter = filters.NumberFilter(field_name='diameter', lookup_expr='exact')
    min_diameter = filters.NumberFilter(field_name='diameter', lookup_expr='gte')
    max_diameter = filters.NumberFilter(field_name='diameter', lookup_expr='lte')
    width = filters.NumberFilter(field_name='width', lookup_expr='exact')
    min_width = filters.NumberFilter(field_name='width', lookup_expr='gte')
    max_width = filters.NumberFilter(field_name='width', lookup_expr='lte')
    profile = filters.NumberFilter(field_name='profile', lookup_expr='exact')
    min_profile = filters.NumberFilter(field_name='profile', lookup_expr='gte')
    max_profile = filters.NumberFilter(field_name='profile', lookup_expr='lte')
    is_available = filters.BooleanFilter(method='filter_is_available')
    has_discount = filters.BooleanFilter(method='filter_has_discount')

    class Meta:
        model = Product
        fields = {
            'in_stock': ['exact'],
            'category': ['exact'],
            'brand': ['exact'],
            'diameter': ['exact', 'in'],
            'width': ['exact'],
            'profile': ['exact'],
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
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [filters.DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    ordering = ['name']

    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class BrandDetailView(generics.RetrieveAPIView):
    queryset = Brand.objects.all()
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
    ordering_fields = ['price', 'created_at', 'name', 'diameter', 'width', 'profile']
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
