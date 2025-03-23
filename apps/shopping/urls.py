from django.urls import path
from .views import (
    CartItemListCreateView,
    CartItemDetailView,
    CartSummaryView,
)

app_name = 'shopping'

urlpatterns = [
    path('', CartItemListCreateView.as_view(), name='cart-list'),
    path('summary/', CartSummaryView.as_view(), name='cart-summary'),
    path('<uuid:id>/', CartItemDetailView.as_view(), name='cart-detail'),
] 