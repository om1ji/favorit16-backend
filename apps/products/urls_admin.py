from django.urls import path
from .views_admin import (
    DashboardView,
    AdminProductListView,
    AdminProductDetailView,
    ImageUploadView,
    AdminCategoryListView,
    AdminCategorySelectView
)

app_name = 'products-admin'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='admin-dashboard'),
    path('products/', AdminProductListView.as_view(), name='admin-product-list'),
    path('products/<uuid:pk>/', AdminProductDetailView.as_view(), name='admin-product-detail'),
    path('upload/image/', ImageUploadView.as_view(), name='admin-image-upload'),
    path('categories/', AdminCategoryListView.as_view(), name='admin-category-list'),
    path('categories/select/', AdminCategorySelectView.as_view(), name='admin-category-select'),
] 