from rest_framework import serializers
from apps.products.serializers import ProductListSerializer
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'quantity', 'price', 'total_price')
        read_only_fields = ('id', 'price')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status = serializers.ChoiceField(choices=Order.StatusChoices.choices, read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'status', 'total_amount', 'shipping_address',
            'payment_method', 'items', 'created_at'
        )
        read_only_fields = ('id', 'total_amount', 'created_at')


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('shipping_address', 'payment_method')

    def create(self, validated_data):
        user = self.context['request'].user
        cart_items = user.cart_items.select_related('product').all()

        if not cart_items:
            raise serializers.ValidationError(
                "Cannot create order with empty cart."
            )

        # Calculate total amount
        total_amount = sum(
            item.quantity * item.product.price for item in cart_items
        )

        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            **validated_data
        )

        # Create order items
        order_items = []
        for cart_item in cart_items:
            if cart_item.quantity > cart_item.product.quantity:
                raise serializers.ValidationError(
                    f"Product '{cart_item.product.name}' does not have enough quantity in stock."
                )
            
            order_items.append(OrderItem(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            ))

        OrderItem.objects.bulk_create(order_items)

        # Update product quantities and clear cart
        for cart_item in cart_items:
            product = cart_item.product
            product.quantity -= cart_item.quantity
            if product.quantity == 0:
                product.in_stock = False
            product.save()

        cart_items.delete()

        return order 