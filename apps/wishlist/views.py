from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Favorite
from .serializers import FavoriteSerializer

# Create your views here.

class FavoriteListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('product')


class FavoriteDeleteView(generics.DestroyAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'product_id'

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)
