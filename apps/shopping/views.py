from django.shortcuts import render
from django.db.models import Sum, F
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import CartItem
from .serializers import CartItemSerializer, CartSummarySerializer


class CartItemListCreateView(generics.ListCreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user).select_related('product')


class CartItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CartItemSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = 'id'

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)


class CartSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        
        summary = {
            'items_count': cart_items.count(),
            'total_price': cart_items.aggregate(
                total=Sum(F('quantity') * F('product__price'))
            )['total'] or 0
        }
        
        serializer = CartSummarySerializer(summary)
        return Response(serializer.data)
