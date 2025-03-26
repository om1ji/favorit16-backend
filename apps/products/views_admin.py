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
    AdminCategoryUpdateSerializer
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
            
            # Создаем запись ProductImage в БД
            product_image = ProductImage.objects.create(
                image=image_file,
                alt_text=image_file.name
            )
            
            # Получаем URL изображения с помощью сериализатора
            request_context = {'request': request}
            serializer = AdminProductImageSerializer(product_image, context=request_context)
            
            # Добавляем дополнительные поля для совместимости с предыдущей версией API
            response_data = serializer.data.copy()
            response_data['filename'] = image_file.name
            
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
        # Обработка multipart/form-data для загрузки изображений
        content_type = request.content_type
        print(f"Category create - request content-type: {content_type}")
        
        # Копируем данные для обработки
        data = request.data.copy()
        
        # Проверяем наличие файла изображения
        if 'image' in request.FILES:
            print(f"Received image file for category create: {request.FILES['image'].name}")
        
        serializer = self.get_serializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Устанавливаем заголовок Content-Type
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
        
        # Обработка данных в зависимости от типа контента
        content_type = request.content_type
        print(f"Product update - request content-type: {content_type}")
        
        # Копируем данные для модификации
        data = request.data.copy()
        print(f"Request data: {data}")
        
        # Если Content-Type = application/json
        if 'application/json' in content_type:
            print("Processing JSON request")
            # JSON-запросы уже правильно обрабатываются DRF
        # Если это multipart/form-data, нужна дополнительная обработка
        elif 'multipart/form-data' in content_type:
            print("Processing multipart/form-data request")
            # Обрабатываем поле images если оно есть
            if 'images' in data:
                print(f"Images data type: {type(data['images'])}")
                print(f"Images data: {data['images']}")
                
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
        
        # Передаем контекст запроса в сериализатор
        context = self.get_serializer_context()
        serializer = self.get_serializer(instance, data=data, partial=partial, context=context)
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            print(f"Validation error: {e}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_update(serializer)
        
        # Устанавливаем правильный заголовок Content-Type для ответа
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
        
        # Проверяем наличие файла изображения или поля image_id
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
        print(f"Category update - instance after update: {serializer.instance.image}")
        
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
            
            # Создаем запись в БД непосредственно с файлом изображения
            product_image = ProductImage.objects.create(
                image=image_file,
                alt_text=image_file.name
            )
            
            # Получаем URL изображения
            request_context = {'request': request}
            serializer = AdminProductImageSerializer(product_image, context=request_context)
            
            # Устанавливаем заголовок Content-Type
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
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