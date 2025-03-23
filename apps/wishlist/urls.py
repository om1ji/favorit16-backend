from django.urls import path
from .views import FavoriteListCreateView, FavoriteDeleteView

app_name = 'wishlist'

urlpatterns = [
    path('', FavoriteListCreateView.as_view(), name='favorite-list'),
    path('<uuid:product_id>/', FavoriteDeleteView.as_view(), name='favorite-delete'),
] 