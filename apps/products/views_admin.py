from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters import rest_framework as django_filters
from PIL import Image
import io
import uuid
import os
from .models import Product, Category, ProductImage, Brand
from .serializers_admin import (
    AdminProductDetailSerializer,
    AdminProductImageSerializer,
    AdminCategorySerializer,
    AdminCategorySelectSerializer,
    AdminProductCreateSerializer,
    AdminProductUpdateSerializer,
    AdminCategoryUpdateSerializer,
    AdminBrandSerializer
)
from apps.ordering.models import Order, OrderItem
import json
from rest_framework import serializers


def validate_image_file(image_file):
    # Проверяем MIME тип
    valid_mimes = ['image/jpeg', 'image/png', 'image/gif']
    if not image_file.content_type in valid_mimes:
        raise ValidationError('Unsupported file type. Only JPEG, PNG and GIF are allowed.')
    
    # Проверяем размер файла (максимум 5MB)
    if image_file.size > 5 * 1024 * 1024:
        raise ValidationError('File size too large. Maximum size is 5MB.')
    
    # Проверяем, что файл действительно является изображением
    try:
        img = Image.open(image_file)
        img.verify()
    except:
        raise ValidationError('Invalid image file')


def create_thumbnail(image_file, max_size=(300, 300)):
    img = Image.open(image_file)
    
    # Конвертируем в RGB если изображение в RGBA
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # Сохраняем пропорции
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Сохраняем в буфер
    thumb_io = io.BytesIO()
    img.save(thumb_io, format='JPEG', quality=85)
    return thumb_io


class ImageUploadView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        if 'image' not in request.FILES:
            return Response(
                {'detail': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        try:
            # Валидируем файл
            validate_image_file(image_file)
            
            # Создаем запись в БД
            product_image = ProductImage.objects.create(
                image=image_file,
                alt_text=image_file.name
            )
            
            # Сериализуем и возвращаем результат
            serializer = AdminProductImageSerializer(product_image, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': 'Error processing image'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryImageUploadView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        if 'image' not in request.FILES:
            return Response(
                {'detail': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        try:
            # Валидируем файл
            validate_image_file(image_file)
            
            # Сначала сохраняем изображение напрямую в ProductImage
            # Это позволит сохранить файл с правильным путем через ImageField
            # И вернуть правильный ID для использования в обновлении категории
            product_image = ProductImage.objects.create(
                image=image_file,
                alt_text=image_file.name
            )
            
            # Получаем URL изображения
            image_url = None
            if request:
                image_url = request.build_absolute_uri(product_image.image.url)
            else:
                image_url = product_image.image.url
                
            print(f"Uploaded category image, ID: {product_image.id}, Path: {product_image.image.name}, URL: {image_url}")
            
            # Формируем ответ
            response_data = {
                'id': str(product_image.id),
                'image': image_url,
                'thumbnail': image_url,
                'alt_text': image_file.name,
                'is_feature': False,
                'filename': image_file.name
            }
            
            # Устанавливаем заголовок Content-Type
            response = Response(response_data, status=status.HTTP_201_CREATED)
            response['Content-Type'] = 'application/json'
            return response
            
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"Error in CategoryImageUploadView: {str(e)}")
            return Response(
                {'detail': f'Error processing image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    parent = django_filters.UUIDFilter(field_name='parent__id')

    class Meta:
        model = Category
        fields = ['parent']


class AdminCategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CategoryFilter
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']  # Сортировка по умолчанию
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        # Если запрашиваются все категории без пагинации, отключаем её
        no_pagination = self.request.query_params.get('no_pagination', False)
        if no_pagination and no_pagination.lower() == 'true':
            self.pagination_class = None
            
        return super().get_queryset().select_related('parent').prefetch_related('children')
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data, context=self.get_serializer_context())
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        response = Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        response['Content-Type'] = 'application/json'
        return response
        
    def perform_create(self, serializer):
        serializer.save()


class AdminCategorySelectView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySelectSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        # Получаем только корневые категории
        queryset = Category.objects.filter(parent=None).prefetch_related('children')
        
        # Добавляем уровень вложенности и имена предков
        def annotate_level(categories, level=0, ancestors_names=None):
            if ancestors_names is None:
                ancestors_names = []
            
            for category in categories:
                category.level = level
                category.ancestors_names = ancestors_names
                if hasattr(category, 'children'):
                    annotate_level(
                        category.children.all(),
                        level + 1,
                        ancestors_names + [category.name]
                    )
        
        categories = list(queryset)
        annotate_level(categories)
        return categories


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.UUIDFilter(field_name='category__id')
    status = django_filters.ChoiceFilter(
        choices=[('in_stock', 'In Stock'), ('out_of_stock', 'Out of Stock')],
        method='filter_status'
    )

    class Meta:
        model = Product
        fields = ['category', 'in_stock']

    def filter_status(self, queryset, name, value):
        if value == 'in_stock':
            return queryset.filter(in_stock=True, quantity__gt=0)
        elif value == 'out_of_stock':
            return queryset.filter(Q(in_stock=False) | Q(quantity=0))
        return queryset


class AdminProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    permission_classes = [IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = ProductFilter
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminProductCreateSerializer
        return AdminProductDetailSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            'category'
        ).prefetch_related(
            'images'
        )
        
    def create(self, request, *args, **kwargs):
        # Обработка данных в зависимости от типа контента
        content_type = request.content_type
        print(f"Product create - request content-type: {content_type}")
        
        # Копируем данные для обработки
        data = request.data.copy()
        print(f"Product create - request data: {data}")
        
        # Проверяем наличие и формат images
        if 'images' in data:
            print(f"Product create - images type: {type(data['images'])}")
            print(f"Product create - images: {data['images']}")
            
            # Если images пришло как строка, пытаемся распарсить её как JSON
            if isinstance(data['images'], str):
                try:
                    # Удаляем лишние пробелы
                    images_str = data['images'].strip()
                    
                    # Обрабатываем экранированные кавычки
                    images_str = images_str.replace('\\"', '"').replace("\\'", "'")
                    if images_str.startswith('"') and images_str.endswith('"'):
                        images_str = images_str[1:-1]  # Убираем обрамляющие кавычки
                    
                    data['images'] = json.loads(images_str)
                    print(f"Parsed images: {data['images']}")
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    return Response(
                        {'detail': f'Invalid JSON for images field: {str(e)}', 'value': images_str}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        serializer = self.get_serializer(data=data, context=self.get_serializer_context())
        
        try:
            serializer.is_valid(raise_exception=True)
            print(f"Product create - validated data: {serializer.validated_data}")
        except serializers.ValidationError as e:
            print(f"Product create - validation error: {e}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Устанавливаем заголовок Content-Type
        response = Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        response['Content-Type'] = 'application/json'
        return response


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AdminProductUpdateSerializer
        return AdminProductDetailSerializer

    def get_queryset(self):
        return super().get_queryset().select_related(
            'category',
            'brand'
        ).prefetch_related(
            'images'
        )
        
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        content_type = request.content_type
        data = request.data.copy()
        
        if 'multipart/form-data' in content_type:
            if 'images' in data:
                if isinstance(data['images'], str):
                    try:
                        images_str = data['images'].strip()
                        
                        images_str = images_str.replace('\\"', '"').replace("\\'", "'")
                        if images_str.startswith('"') and images_str.endswith('"'):
                            images_str = images_str[1:-1]
                        
                        data['images'] = json.loads(images_str)
                    except json.JSONDecodeError as e:
                        return Response(
                            {'detail': f'Invalid JSON for images field: {str(e)}', 'value': images_str}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
        
        context = self.get_serializer_context()
        serializer = self.get_serializer(instance, data=data, partial=partial, context=context)
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_update(serializer)
        
        response = Response(serializer.data)
        response['Content-Type'] = 'application/json'
        return response

    def handle_exception(self, exc):
        if isinstance(exc, Product.DoesNotExist):
            return Response(
                {"detail": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        return super().handle_exception(exc)


class DashboardView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Базовые метрики
        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        
        orders = Order.objects.all()
        total_orders = orders.count()
        total_revenue = orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        products_sold = OrderItem.objects.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        # Последние заказы
        recent_orders = orders.order_by('-created_at')[:5].values(
            'id',
            'created_at',
            'status',
            'total_amount'
        )
        
        # Топ продуктов
        top_products = OrderItem.objects.values(
            'product_id',
            'product__name'
        ).annotate(
            total_sales=Sum('quantity')
        ).order_by('-total_sales')[:5]
        
        # Выручка по категориям
        revenue_by_category = OrderItem.objects.values(
            'product__category__name'
        ).annotate(
            revenue=Sum(F('quantity') * F('price'))
        ).order_by('-revenue')
        
        # Заказы по статусам
        orders_by_status = orders.values(
            'status'
        ).annotate(
            count=Count('id')
        )
        
        return Response({
            'total_products': total_products,
            'total_categories': total_categories,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'products_sold': products_sold,
            'recent_orders': [
                {
                    'id': str(order['id']),
                    'created_at': order['created_at'].isoformat(),
                    'status': order['status'],
                    'total': float(order['total_amount'])
                } for order in recent_orders
            ],
            'top_products': [
                {
                    'id': str(item['product_id']),
                    'name': item['product__name'],
                    'total_sales': item['total_sales']
                } for item in top_products
            ],
            'revenue_by_category': [
                {
                    'category': item['product__category__name'],
                    'revenue': float(item['revenue'])
                } for item in revenue_by_category
            ],
            'orders_by_status': {
                item['status']: item['count']
                for item in orders_by_status
            }
        })


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AdminCategoryUpdateSerializer
        return AdminCategorySerializer

    def get_queryset(self):
        return super().get_queryset().select_related('parent').prefetch_related('children')
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Получаем информацию о типе запроса
        content_type = request.content_type
        print(f"Category update - request content-type: {content_type}")
        
        # Копируем данные для обработки
        data = request.data.copy()
        print(f"Category update - request data: {data}")
        
        # Проверяем, есть ли файл изображения или поле image_id
        if 'image' in request.FILES:
            # Файл уже включен в data через request.data, дополнительная обработка не требуется
            print(f"Received image file: {request.FILES['image'].name}")
        elif 'image_id' in data:
            print(f"Received image_id: {data['image_id']}")
        
        # Передаем контекст запроса в сериализатор
        context = self.get_serializer_context()
        serializer = self.get_serializer(instance, data=data, partial=partial, context=context)
        
        try:
            serializer.is_valid(raise_exception=True)
            print(f"Category update - validated data: {serializer.validated_data}")
        except serializers.ValidationError as e:
            print(f"Category update - validation error: {e}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_update(serializer)
        
        # Проверяем результат обновления
        updated_instance = self.get_object()  # Получаем обновленный экземпляр из БД
        if updated_instance.image:
            image_url = None
            request_context = self.get_serializer_context().get('request')
            if request_context:
                image_url = request_context.build_absolute_uri(updated_instance.image.url)
            else:
                image_url = updated_instance.image.url
            print(f"Category updated with image: {updated_instance.image}, URL: {image_url}")
        else:
            print("Category updated without image")
        
        # Устанавливаем заголовок Content-Type
        response = Response(serializer.data)
        response['Content-Type'] = 'application/json'
        return response
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Проверяем, есть ли связанные товары
        if instance.products.exists():
            return Response(
                {"detail": "Невозможно удалить категорию, так как с ней связаны товары."},
                status=status.HTTP_409_CONFLICT
            )
        
        # Проверяем, есть ли подкатегории
        if instance.children.exists():
            return Response(
                {"detail": "Невозможно удалить категорию, так как у неё есть подкатегории."},
                status=status.HTTP_409_CONFLICT
            )
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageUploadView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        if 'image' not in request.FILES:
            return Response(
                {'detail': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image_file = request.FILES['image']
        
        try:
            # Валидируем файл
            validate_image_file(image_file)
            
            # Создаем запись в БД напрямую с файлом изображения
            product_image = ProductImage.objects.create(
                image=image_file,
                alt_text=image_file.name
            )
            
            # Получаем URL изображения
            image_url = None
            if request:
                image_url = request.build_absolute_uri(product_image.image.url)
            else:
                image_url = product_image.image.url
                
            print(f"Uploaded product image, ID: {product_image.id}, Path: {product_image.image.name}, URL: {image_url}")
            
            # Формируем ответ
            response_data = {
                'id': str(product_image.id),
                'image': image_url,
                'thumbnail': image_url,
                'alt_text': image_file.name,
                'is_feature': False,
                'filename': image_file.name
            }
            
            # Устанавливаем заголовок Content-Type
            response = Response(response_data, status=status.HTTP_201_CREATED)
            response['Content-Type'] = 'application/json'
            return response
            
        except ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"Error in ProductImageUploadView: {str(e)}")
            return Response(
                {'detail': f'Error processing image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminBrandListView(generics.ListAPIView):
    """
    Представление для получения списка брендов для админки.
    Поддерживает фильтрацию по категории.
    """
    queryset = Brand.objects.select_related('category').all()
    serializer_class = AdminBrandSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ['category']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Если в параметрах запроса есть category, фильтруем по нему
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
            
        return queryset


class ProductImageDeleteView(APIView):
    """
    Представление для удаления изображений товаров.
    """
    permission_classes = [IsAdminUser]
    
    def delete(self, request, image_id):
        try:
            # Находим изображение по ID
            image = ProductImage.objects.get(id=image_id)
            
            # Сохраняем информацию о товаре для логирования
            product_id = image.product.id if image.product else None
            image_path = image.image.name if image.image else None
            
            print(f"Deleting image {image_id}, product: {product_id}, path: {image_path}")
            
            # Удаляем файл с диска
            if image.image:
                try:
                    image.image.delete(save=False)
                    print(f"Deleted image file: {image_path}")
                except Exception as e:
                    print(f"Error deleting image file: {e}")
            
            # Удаляем запись из базы данных
            image.delete()
            print(f"Deleted image record: {image_id}")
            
            return Response(
                {'detail': 'Image deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except ProductImage.DoesNotExist:
            return Response(
                {'detail': 'Image not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error deleting image {image_id}: {str(e)}")
            return Response(
                {'detail': f'Error deleting image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminProductImageListView(generics.ListAPIView):
    """
    Представление для получения списка всех изображений товаров.
    Полезно для управления неиспользуемыми изображениями.
    """
    queryset = ProductImage.objects.all()
    serializer_class = AdminProductImageSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр для неиспользуемых изображений
        unused = self.request.query_params.get('unused')
        if unused and unused.lower() == 'true':
            queryset = queryset.filter(product__isnull=True)
            
        # Фильтр по товару
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
            
        return queryset.order_by('-created_at')


class CleanupUnusedImagesView(APIView):
    """
    Представление для очистки неиспользуемых изображений.
    Удаляет все изображения, которые не привязаны к товарам или категориям.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        try:
            # Находим все неиспользуемые изображения
            unused_images = ProductImage.objects.filter(product__isnull=True)
            
            # Также проверяем изображения, которые не используются в категориях
            # (для этого нужно проверить, не используется ли путь изображения в Category.image)
            from .models import Category
            used_image_paths = set()
            
            # Собираем все пути изображений, используемых в категориях
            for category in Category.objects.exclude(image='').exclude(image__isnull=True):
                if category.image:
                    used_image_paths.add(category.image.name)
            
            deleted_count = 0
            deleted_files = []
            
            for image in unused_images:
                # Проверяем, не используется ли это изображение в категориях
                if image.image and image.image.name not in used_image_paths:
                    image_path = image.image.name
                    image_id = str(image.id)
                    
                    print(f"Deleting unused image: {image_id}, path: {image_path}")
                    
                    # Удаляем файл с диска
                    try:
                        image.image.delete(save=False)
                        print(f"Deleted image file: {image_path}")
                    except Exception as e:
                        print(f"Error deleting image file {image_path}: {e}")
                    
                    # Удаляем запись из БД
                    image.delete()
                    
                    deleted_count += 1
                    deleted_files.append({
                        'id': image_id,
                        'path': image_path
                    })
            
            return Response({
                'detail': f'Successfully deleted {deleted_count} unused images',
                'deleted_count': deleted_count,
                'deleted_files': deleted_files
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            return Response(
                {'detail': f'Error during cleanup: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 