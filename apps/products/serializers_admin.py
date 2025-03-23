from rest_framework import serializers
import json
from .models import Product, Category, ProductImage, Brand


class AdminProductImageSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'thumbnail', 'alt_text', 'is_feature')

    def get_thumbnail(self, obj):
        return obj.image.url  # В реальном проекте здесь будет URL миниатюры


class AdminBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'name', 'logo')


class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'parent')


class AdminCategorySelectSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    full_name = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'level', 'full_name', 'children')

    def get_full_name(self, obj):
        if not hasattr(obj, 'ancestors_names'):
            return obj.name
        return ' > '.join(obj.ancestors_names + [obj.name])

    def get_children(self, obj):
        children = obj.children.all()
        if children:
            return AdminCategorySelectSerializer(children, many=True).data
        return None


class AdminProductCreateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), required=False)
    images = serializers.CharField(required=False)  # Будем парсить вручную
    images_metadata = serializers.CharField(required=False)  # Будем парсить вручную

    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'brand',
            'price',
            'old_price',
            'description',
            'in_stock',
            'quantity',
            'diameter',
            'width',
            'profile',
            'images',
            'images_metadata'
        )

    def validate_images(self, value):
        if not value:
            return []
        try:
            images_list = json.loads(value)
            if not isinstance(images_list, list):
                raise serializers.ValidationError("Must be a JSON array of UUIDs")
            # Проверяем каждый UUID
            for image_id in images_list:
                try:
                    ProductImage.objects.get(id=image_id)
                except (ProductImage.DoesNotExist, ValueError):
                    raise serializers.ValidationError(f"Invalid image ID: {image_id}")
            return images_list
        except json.JSONDecodeError:
            raise serializers.ValidationError("Must be a valid JSON array")

    def validate_images_metadata(self, value):
        if not value:
            return []
        try:
            metadata_list = json.loads(value)
            if not isinstance(metadata_list, list):
                raise serializers.ValidationError("Must be a JSON array of objects")
            # Проверяем структуру каждого объекта метаданных
            for item in metadata_list:
                if not isinstance(item, dict):
                    raise serializers.ValidationError("Each item must be an object")
                if 'image_id' not in item:
                    raise serializers.ValidationError("Each item must have 'image_id'")
            return metadata_list
        except json.JSONDecodeError:
            raise serializers.ValidationError("Must be a valid JSON array")

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        images_metadata = validated_data.pop('images_metadata', [])
        
        # Создаем продукт
        product = super().create(validated_data)
        
        # Обрабатываем изображения
        if images:
            metadata_dict = {
                str(item['image_id']): item 
                for item in images_metadata
            } if images_metadata else {}
            
            feature_image = None
            for image_id in images:
                try:
                    image = ProductImage.objects.get(id=image_id)
                    metadata = metadata_dict.get(str(image_id), {})
                    
                    image.product = product
                    image.alt_text = metadata.get('alt_text', '')
                    image.is_feature = metadata.get('is_feature', False)
                    image.save()
                    
                    if metadata.get('is_feature'):
                        feature_image = image
                except ProductImage.DoesNotExist:
                    continue  # Пропускаем несуществующие изображения
            
            # Устанавливаем главное изображение
            if feature_image:
                product.set_feature_image(feature_image)
            elif images:  # Если нет отмеченного главного изображения, используем первое
                product.set_feature_image(images[0])
        
        return product


class AdminProductDetailSerializer(serializers.ModelSerializer):
    category = AdminCategorySerializer()
    brand = AdminBrandSerializer()
    images = AdminProductImageSerializer(many=True)
    tire_size = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = (
            'id',
            'name',
            'category',
            'brand',
            'price',
            'old_price',
            'description',
            'in_stock',
            'quantity',
            'diameter',
            'width',
            'profile',
            'tire_size',
            'images'
        )
        
    def get_tire_size(self, obj):
        """Return formatted tire size (width/profile R diameter)"""
        if obj.width and obj.profile and obj.diameter:
            return f"{obj.width}/{obj.profile} R{obj.diameter}"
        return None