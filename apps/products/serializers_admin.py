from rest_framework import serializers
import json
from .models import Product, Category, ProductImage, Brand


class AdminProductImageSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'thumbnail', 'alt_text', 'is_feature')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class AdminBrandSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    logo = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ('id', 'name', 'logo', 'category', 'category_name')
        
    def get_logo(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url if obj.logo else None


class AdminCategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image', 'parent', 'children', 'created_at', 'updated_at')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
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
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class AdminProductCreateSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), required=False)
    images = serializers.JSONField(required=False)  # Принимает как строки, так и JSON
    images_metadata = serializers.JSONField(required=False)  # Принимает как строки, так и JSON

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
            # Общие поля
            'diameter',
            # Поля для шин
            'width',
            'profile',
            # Поля для дисков
            'wheel_width',
            'et_offset',
            'pcd',
            'bolt_count',
            'center_bore',
            # Изображения
            'images',
            'images_metadata'
        )

    def validate(self, data):
        """Валидация: бренд должен принадлежать той же категории, что и товар"""
        category = data.get('category')
        brand = data.get('brand')
        
        if brand and category and brand.category != category:
            raise serializers.ValidationError({
                'brand': 'Brand must belong to the same category as the product.'
            })
        
        return data

    def validate_images(self, value):
        if not value:
            return []
        
        print(f"validate_images received: {value}, type: {type(value)}")
        
        # Если value уже список (из JSON-запроса), используем его
        if isinstance(value, list):
            images_list = value
        # Если value - строка, пытаемся преобразовать в JSON
        elif isinstance(value, str):
            try:
                images_list = json.loads(value)
                if not isinstance(images_list, list):
                    raise serializers.ValidationError("Must be a JSON array of UUIDs or objects")
            except json.JSONDecodeError:
                raise serializers.ValidationError("Must be a valid JSON array")
        else:
            raise serializers.ValidationError("Invalid format for images")
        
        # Проверяем каждый элемент
        result = []
        for img in images_list:
            # Если это строка, считаем ее ID изображения
            if isinstance(img, str):
                image_id = img
                try:
                    ProductImage.objects.get(id=image_id)
                    result.append(img)  # Добавляем ID как есть
                except (ProductImage.DoesNotExist, ValueError):
                    raise serializers.ValidationError(f"Invalid image ID: {image_id}")
            # Если это объект, извлекаем ID и проверяем
            elif isinstance(img, dict):
                if 'id' not in img:
                    raise serializers.ValidationError("Each image object must have 'id' field")
                
                image_id = img['id']
                try:
                    ProductImage.objects.get(id=image_id)
                    # Добавляем весь объект для последующей обработки
                    result.append(img)
                except (ProductImage.DoesNotExist, ValueError):
                    raise serializers.ValidationError(f"Invalid image ID: {image_id}")
            else:
                raise serializers.ValidationError("Each image must be a string UUID or an object with id")
            
        return result

    def validate_images_metadata(self, value):
        if not value:
            return []
        
        # Если value уже список (из JSON-запроса), используем его
        if isinstance(value, list):
            metadata_list = value
        # Если value - строка, пытаемся преобразовать в JSON
        elif isinstance(value, str):
            try:
                metadata_list = json.loads(value)
                if not isinstance(metadata_list, list):
                    raise serializers.ValidationError("Must be a JSON array of objects")
            except json.JSONDecodeError:
                raise serializers.ValidationError("Must be a valid JSON array")
        else:
            raise serializers.ValidationError("Invalid format for images_metadata")
        
        # Проверяем структуру каждого объекта метаданных
        for item in metadata_list:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each item must be an object")
            if 'image_id' not in item:
                raise serializers.ValidationError("Each item must have 'image_id'")
        return metadata_list

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        images_metadata = validated_data.pop('images_metadata', [])
        
        print(f"create - images: {images}, type: {type(images)}")
        
        # Создаем продукт
        product = super().create(validated_data)
        
        # Обрабатываем изображения
        if images:
            # Преобразуем images_metadata в словарь по image_id для быстрого доступа
            metadata_dict = {
                str(item['image_id']): item 
                for item in images_metadata
            } if images_metadata else {}
            
            feature_image = None
            
            for image_item in images:
                try:
                    # Определяем тип данных изображения (строка ID или объект)
                    if isinstance(image_item, str):
                        # Если передан только ID
                        image_id = image_item
                        image = ProductImage.objects.get(id=image_id)
                        # Берем метаданные из images_metadata
                        metadata = metadata_dict.get(str(image_id), {})
                        is_feature = metadata.get('is_feature', False)
                        alt_text = metadata.get('alt_text', '')
                    else:
                        # Если передан объект с ID и другими полями
                        image_id = image_item['id']
                        image = ProductImage.objects.get(id=image_id)
                        is_feature = image_item.get('is_feature', False)
                        alt_text = image_item.get('alt_text', image.alt_text)
                    
                    # Обновляем данные изображения
                    image.product = product
                    image.alt_text = alt_text
                    image.is_feature = is_feature
                    image.save()
                    
                    print(f"Added image to product: {image_id}, is_feature: {is_feature}")
                    
                    # Запоминаем главное изображение
                    if is_feature:
                        feature_image = image
                        
                except ProductImage.DoesNotExist:
                    print(f"Image not found: {image_id if isinstance(image_item, str) else image_item.get('id')}")
                    continue  # Пропускаем несуществующие изображения
            
            # Устанавливаем главное изображение
            if feature_image:
                product.set_feature_image(feature_image)
                print(f"Set feature image: {feature_image.id}")
            elif images:  # Если нет отмеченного главного изображения, используем первое
                try:
                    first_image_data = images[0]
                    first_image_id = first_image_data if isinstance(first_image_data, str) else first_image_data['id']
                    first_image = ProductImage.objects.get(id=first_image_id)
                    product.set_feature_image(first_image)
                    print(f"Set first image as feature: {first_image.id}")
                except ProductImage.DoesNotExist:
                    print(f"First image not found for feature")
                    pass
        
        return product
        
    def to_representation(self, instance):
        """
        Преобразуем объект в представление JSON.
        Используем AdminProductDetailSerializer для полного представления.
        """
        return AdminProductDetailSerializer(instance, context=self.context).data


class AdminProductDetailSerializer(serializers.ModelSerializer):
    category = AdminCategorySerializer()
    brand = AdminBrandSerializer()
    images = AdminProductImageSerializer(many=True)
    tire_size = serializers.SerializerMethodField()
    wheel_size = serializers.SerializerMethodField()
    
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
            # Общие поля
            'diameter',
            # Поля для шин
            'width',
            'profile',
            'tire_size',
            # Поля для дисков
            'wheel_width',
            'et_offset',
            'pcd',
            'bolt_count',
            'center_bore',
            'wheel_size',
            # Изображения
            'images'
        )
        
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
            # Общие поля
            'diameter',
            # Поля для шин
            'width',
            'profile',
            # Поля для дисков
            'wheel_width',
            'et_offset',
            'pcd',
            'bolt_count',
            'center_bore',
            # Изображения
            'images'
        )
        
    def validate(self, data):
        """Валидация: бренд должен принадлежать той же категории, что и товар"""
        category = data.get('category')
        brand = data.get('brand')
        
        # Если бренд не указан, валидация проходит
        if not brand:
            return data
            
        # Если категория не изменяется, берем текущую категорию из instance
        if not category and hasattr(self, 'instance'):
            category = self.instance.category
            
        if brand and category and brand.category != category:
            raise serializers.ValidationError({
                'brand': 'Brand must belong to the same category as the product.'
            })
        
        return data

    def validate_images(self, value):
        """Валидируем данные изображений"""
        print(f"validate_images received: {value}, type: {type(value)}")
        
        if value is None:
            return []
            
        # Если value уже список (из JSON-запроса), просто используем его
        if isinstance(value, list):
            print(f"Value is already a list: {value}")
            return value
            
        # Если value - строка, пытаемся преобразовать в JSON
        if isinstance(value, str):
            try:
                # Удаляем лишние пробелы и символы
                value = value.strip()
                # Проверяем, не является ли строка строковым представлением списка со строковыми элементами
                if value.startswith("['") or value.startswith('["'):
                    # Это строковое представление списка со строками, нужно преобразовать его в правильный JSON
                    import ast
                    value = ast.literal_eval(value)
                else:
                    value = json.loads(value)
                print(f"Parsed JSON in validator: {value}")
            except (json.JSONDecodeError, SyntaxError, ValueError) as e:
                print(f"JSON/Value error in validator: {e}")
                raise serializers.ValidationError(f"Images must be a valid JSON string: {str(e)}")
            
        if not isinstance(value, list):
            print(f"Not a list: {value}")
            raise serializers.ValidationError("Images must be a list")
            
        # Проверяем формат каждого изображения
        result = []
        for img in value:
            if isinstance(img, str):
                # Пытаемся интерпретировать строку как UUID
                try:
                    image_id = img
                    # Проверяем существование изображения
                    try:
                        ProductImage.objects.get(id=image_id)
                    except (ProductImage.DoesNotExist, ValueError):
                        raise serializers.ValidationError(f"Invalid image ID: {image_id}")
                    # Преобразуем в формат словаря
                    img = {'id': image_id, 'is_feature': False, 'alt_text': ''}
                except Exception as e:
                    raise serializers.ValidationError(f"Invalid image format: {str(e)}")
            elif not isinstance(img, dict):
                raise serializers.ValidationError("Each image must be an object or UUID string")
                
            if 'id' not in img:
                raise serializers.ValidationError("Each image must have an id")
            
            result.append(img)
                
        return result
    
    def update(self, instance, validated_data):
        # Обрабатываем изображения, если они переданы
        images_data = validated_data.pop('images', [])
        print(f"Update method received images_data: {images_data}")
        
        # Обновляем остальные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Обрабатываем изображения
        if images_data is not None:  # Проверяем на None, а не на пустоту, чтобы обрабатывать пустые списки
            # Получаем текущие изображения продукта
            current_images = {str(image.id): image for image in instance.images.all()}
            new_image_ids = set()
            feature_image = None
            
            for image_data in images_data:
                # Если image_data - строка или словарь только с id, преобразуем его
                if isinstance(image_data, str):
                    image_id = image_data
                    is_feature = False
                    alt_text = ""
                elif isinstance(image_data, dict) and len(image_data.keys()) == 1 and 'id' in image_data:
                    image_id = image_data['id']
                    is_feature = False
                    alt_text = ""
                else:
                    image_id = image_data.get('id')
                    is_feature = image_data.get('is_feature', False)
                    alt_text = image_data.get('alt_text', '')
                
                try:
                    # Пытаемся найти существующее изображение
                    print(f"Looking for image with ID: {image_id}")
                    image = ProductImage.objects.get(id=image_id)
                    print(f"Found image: {image}")
                    
                    # Привязываем изображение к продукту
                    image.product = instance
                    image.alt_text = alt_text
                    image.is_feature = is_feature
                    image.save()
                    
                    new_image_ids.add(str(image.id))
                    
                    # Запоминаем главное изображение
                    if is_feature:
                        feature_image = image
                except (ProductImage.DoesNotExist, ValueError) as e:
                    # Пропускаем несуществующие изображения
                    print(f"Error with image {image_id}: {e}")
                    continue
            
            # Удаляем изображения, которые больше не связаны с продуктом
            images_to_remove = set(current_images.keys()) - new_image_ids
            if images_to_remove:
                print(f"Removing images: {images_to_remove}")
                images_to_delete = ProductImage.objects.filter(id__in=images_to_remove)
                
                # Удаляем файлы с диска и записи из БД
                for image_to_delete in images_to_delete:
                    print(f"Deleting image: {image_to_delete.id}, path: {image_to_delete.image.name}")
                    
                    # Удаляем файл с диска
                    if image_to_delete.image:
                        try:
                            image_to_delete.image.delete(save=False)
                            print(f"Deleted image file: {image_to_delete.image.name}")
                        except Exception as e:
                            print(f"Error deleting image file: {e}")
                    
                    # Удаляем запись из БД
                    image_to_delete.delete()
                    print(f"Deleted image record: {image_to_delete.id}")
            
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


class AdminCategoryUpdateSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)
    image = serializers.CharField(required=False, allow_null=True)
    image_id = serializers.CharField(required=False, allow_null=True, write_only=True)
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image', 'image_id', 'parent')
    
    def validate_image(self, value):
        """Валидируем строку с путем к изображению"""
        if not value:
            return None
            
        # Если значение - строка с путем к изображению
        if isinstance(value, str):
            # Если путь начинается с /media/, убираем этот префикс
            if value.startswith('/media/'):
                return value[7:]  # Убираем '/media/' из пути
            return value
            
        return value
    
    def validate(self, data):
        """Дополнительная валидация для обработки image_id"""
        # Если есть image_id, получаем изображение и используем его путь
        if 'image_id' in data and data['image_id']:
            from .models import ProductImage
            try:
                image = ProductImage.objects.get(id=data['image_id'])
                print(f"Found image with id {data['image_id']}: {image.image.url}")
                
                # Вместо создания нового файла, просто копируем информацию о пути
                # Прямое присваивание ImageField к полю категории
                data.pop('image_id')
                data['image'] = image.image
                print(f"Using image path: {image.image}")
                
            except ProductImage.DoesNotExist:
                raise serializers.ValidationError({"image_id": "Изображение с указанным ID не найдено"})
            except Exception as e:
                print(f"Error processing image_id: {str(e)}")
                raise serializers.ValidationError({"image_id": f"Ошибка обработки изображения: {str(e)}"})
                
        return data
        
    def update(self, instance, validated_data):
        # Обновляем поля категории
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance
        
    def to_representation(self, instance):
        """
        Используем полный сериализатор для отображения результата.
        """
        return AdminCategorySerializer(instance, context=self.context).data