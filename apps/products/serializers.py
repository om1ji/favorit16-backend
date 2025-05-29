from rest_framework import serializers
from .models import Category, Product, ProductImage, Brand


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'is_feature', 'created_at')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class BrandSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Brand
        fields = ('id', 'name', 'logo', 'category', 'category_name', 'created_at')
        
    def get_logo(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image', 'parent', 'children')

    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    brand = BrandSerializer()
    feature_image = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    tire_size = serializers.SerializerMethodField(read_only=True)
    wheel_size = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'price', 'old_price', 'category', 'brand',
            'diameter',
            'width', 'profile', 'tire_size',
            'wheel_width', 'et_offset', 'pcd', 'bolt_count', 'center_bore', 'wheel_size',
            'feature_image', 'images', 'in_stock', 'quantity', 'is_available',
            'has_discount', 'discount_percentage', 'created_at'
        )

    def get_feature_image(self, obj):
        feature_image = obj.images.filter(is_feature=True).first()
        if feature_image:
            return ProductImageSerializer(feature_image, context=self.context).data
        return None
        
    def get_tire_size(self, obj):
        """Return formatted tire size (width/profile R diameter)"""
        if obj.width and obj.profile and obj.diameter:
            return f"{obj.width}/{obj.profile} R{obj.diameter}"
        return None
        
    def get_wheel_size(self, obj):
        """Return formatted wheel size (diameter x wheel_width ET offset PCD bolt_count x center_bore)"""
        if obj.diameter and obj.wheel_width:
            size_parts = [f"{obj.diameter}x{obj.wheel_width}"]
            
            if obj.et_offset is not None:
                size_parts.append(f"ET{obj.et_offset}")
                
            if obj.pcd and obj.bolt_count:
                size_parts.append(f"{obj.bolt_count}x{obj.pcd}")
                
            if obj.center_bore:
                size_parts.append(f"DIA{obj.center_bore}")
                
            return " ".join(size_parts)
        return None


class ProductDetailSerializer(ProductListSerializer):
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ('description',) 