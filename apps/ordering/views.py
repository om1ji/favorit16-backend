from django.shortcuts import render
from rest_framework import generics, permissions
from django.db.models import Prefetch
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer


class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('product')
            )
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        return OrderSerializer


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'id'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItem.objects.select_related('product')
            )
        )
