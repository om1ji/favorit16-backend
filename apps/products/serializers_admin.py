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
    image = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image', 'parent', 'children', 'created_at', 'updated_at')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
        
    def get_children(self, obj):
        children = obj.children.all()
        if children:
            return AdminCategorySerializer(children, many=True, context=self.context).data
        return []


class AdminCategorySelectSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(read_only=True)
    full_name = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image', 'parent', 'level', 'full_name', 'children', 'created_at', 'updated_at')

    def get_full_name(self, obj):
        if not hasattr(obj, 'ancestors_names'):
            return obj.name
        return ' > '.join(obj.ancestors_names + [obj.name])

    def get_children(self, obj):
        children = obj.children.all()
        if children:
            return AdminCategorySelectSerializer(children, many=True, context=self.context).data
        return []
        
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
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


class AdminProductUpdateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), required=False, allow_null=True)
    images = serializers.JSONField(required=False)  # JSON массив с информацией об изображениях
    
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
            'images'
        )
        
    def validate_images(self, value):
        """Валидируем данные изображений"""
        if not value:
            return []
            
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Images must be a valid JSON string")
            
        if not isinstance(value, list):
            raise serializers.ValidationError("Images must be a list")
            
        # Проверяем формат каждого изображения
        for img in value:
            if not isinstance(img, dict):
                raise serializers.ValidationError("Each image must be an object")
                
            if 'id' not in img:
                raise serializers.ValidationError("Each image must have an id")
                
        return value
    
    def update(self, instance, validated_data):
        # Обрабатываем изображения, если они переданы
        images_data = validated_data.pop('images', [])
        
        # Обновляем остальные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Обрабатываем изображения
        if images_data:
            # Получаем текущие изображения продукта
            current_images = {str(image.id): image for image in instance.images.all()}
            new_image_ids = set()
            feature_image = None
            
            for image_data in images_data:
                image_id = image_data.get('id')
                is_feature = image_data.get('is_feature', False)
                alt_text = image_data.get('alt_text', '')
                
                try:
                    # Пытаемся найти существующее изображение
                    image = ProductImage.objects.get(id=image_id)
                    
                    # Привязываем изображение к продукту
                    image.product = instance
                    image.alt_text = alt_text
                    image.is_feature = is_feature
                    image.save()
                    
                    new_image_ids.add(str(image.id))
                    
                    # Запоминаем главное изображение
                    if is_feature:
                        feature_image = image
                except (ProductImage.DoesNotExist, ValueError):
                    # Пропускаем несуществующие изображения
                    continue
            
            # Удаляем привязку к изображениям, которые больше не связаны с продуктом
            images_to_remove = set(current_images.keys()) - new_image_ids
            if images_to_remove:
                ProductImage.objects.filter(id__in=images_to_remove).update(product=None)
            
            # Устанавливаем главное изображение
            if feature_image:
                # Сбрасываем is_feature у всех изображений, кроме выбранного
                instance.images.exclude(id=feature_image.id).update(is_feature=False)
                feature_image.is_feature = True
                feature_image.save()
            elif new_image_ids and not instance.images.filter(is_feature=True).exists():
                # Если нет отмеченного главного изображения, используем первое
                first_image = instance.images.first()
                if first_image:
                    first_image.is_feature = True
                    first_image.save()
        
        # Возвращаем обновленный экземпляр продукта с сериализованными изображениями
        # Используем DetailSerializer для полной сериализации всех полей
        return instance

    def to_representation(self, instance):
        """
        Преобразуем объект в представление JSON.
        Используем AdminProductDetailSerializer для полного представления.
        """
        return AdminProductDetailSerializer(instance, context=self.context).data