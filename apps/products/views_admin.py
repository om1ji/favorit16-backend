from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters import rest_framework as filters
from PIL import Image
import io
import uuid
import os
from .models import Product, Category, ProductImage
from .serializers_admin import (
    AdminProductDetailSerializer,
    AdminProductImageSerializer,
    AdminCategorySerializer,
    AdminCategorySelectSerializer,
    AdminProductCreateSerializer
)
from apps.ordering.models import Order, OrderItem


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
            serializer = AdminProductImageSerializer(product_image)
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


class CategoryFilter(filters.FilterSet):
    search = filters.CharFilter(field_name='name', lookup_expr='icontains')
    parent = filters.UUIDFilter(field_name='parent__id')

    class Meta:
        model = Category
        fields = ['parent']


class AdminCategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CategoryFilter
    pagination_class = None  # Отключаем пагинацию для списка категорий

    def get_queryset(self):
        return super().get_queryset().select_related('parent')


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


class ProductFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = filters.UUIDFilter(field_name='category__id')
    status = filters.ChoiceFilter(
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
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ProductFilter
    parser_classes = [MultiPartParser, FormParser]

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
    serializer_class = AdminProductDetailSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return super().get_queryset().select_related(
            'category'
        ).prefetch_related(
            'images'
        )

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