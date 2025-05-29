from django.urls import path
from .views import (
    CategoryListView,
    CategoryDetailView,
    ProductListView,
    ProductDetailView,
    BrandListView,
    BrandDetailView,
)

app_name = 'products'

urlpatterns = [
    # Category endpoints
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<uuid:id>/', CategoryDetailView.as_view(), name='category-detail'),
    path('categories/<uuid:category_id>/brands/', BrandListView.as_view(), name='category-brands'),
    
    # Brand endpoints
    path('brands/', BrandListView.as_view(), name='brand-list'),
    path('brands/<uuid:id>/', BrandDetailView.as_view(), name='brand-detail'),
    
    # Product endpoints
    path('', ProductListView.as_view(), name='product-list'),
    path('<uuid:id>/', ProductDetailView.as_view(), name='product-detail'),
] 