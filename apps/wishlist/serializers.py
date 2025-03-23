from rest_framework import serializers
from apps.products.serializers import ProductListSerializer
from .models import Favorite


class FavoriteSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'product', 'product_id', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_product_id(self, value):
        user = self.context['request'].user
        if Favorite.objects.filter(user=user, product_id=value).exists():
            raise serializers.ValidationError(
                "This product is already in your favorites."
            )
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['product_id'] = validated_data.pop('product_id')
        return super().create(validated_data) 