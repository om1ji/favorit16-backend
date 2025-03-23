from django.urls import path
from .views import OrderListCreateView, OrderDetailView

app_name = 'ordering'

urlpatterns = [
    path('', OrderListCreateView.as_view(), name='order-list'),
    path('<uuid:id>/', OrderDetailView.as_view(), name='order-detail'),
] 