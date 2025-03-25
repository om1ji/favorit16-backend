"""core URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger documentation settings
schema_view = get_schema_view(
    openapi.Info(
        title="Favorit API",
        default_version='v1',
        description="API documentation for Favorit project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="info@favorit-116.ru"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Django Admin interface
    path('admin/', admin.site.urls),
    
    # API documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Admin API endpoints
    path('products-admin/', include('apps.products.urls_admin')),
    
    # Regular API endpoints
    path('users/', include('apps.users.urls')),
    path('products/', include('apps.products.urls')),
    path('cart/', include('apps.shopping.urls')),
    path('orders/', include('apps.ordering.urls')),
    path('wishlist/', include('apps.wishlist.urls')),
]

# Serving media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 