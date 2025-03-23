from rest_framework import serializers
from apps.products.models import Product
from apps.products.serializers import ProductListSerializer
from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = CartItem
        fields = (
            'id', 'product', 'product_id', 'quantity',
            'total_price', 'created_at'
        )
        read_only_fields = ('id', 'created_at')

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value)
            if not product.is_available:
                raise serializers.ValidationError(
                    "This product is currently not available."
                )
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found.")

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )
        return value

    def create(self, validated_data):
        product_id = validated_data.pop('product_id')
        user = self.context['request'].user
        product = Product.objects.get(id=product_id)

        cart_item, created = CartItem.objects.get_or_create(
            user=user,
            product=product,
            defaults={'quantity': validated_data.get('quantity', 1)}
        )

        if not created:
            cart_item.quantity = validated_data.get('quantity', cart_item.quantity)
            cart_item.save()

        return cart_item


class CartSummarySerializer(serializers.Serializer):
    items_count = serializers.IntegerField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2) 