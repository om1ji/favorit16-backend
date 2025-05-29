# Generated manually for brand-category relationship

from django.db import migrations


def populate_brand_categories(apps, schema_editor):
    """
    Распределяем существующие бренды по категориям на основе товаров.
    Если бренд используется в нескольких категориях, создаем дубликаты.
    """
    Brand = apps.get_model('products', 'Brand')
    Category = apps.get_model('products', 'Category')
    Product = apps.get_model('products', 'Product')
    
    # Получаем все существующие бренды
    existing_brands = list(Brand.objects.all())
    
    # Для каждого бренда находим категории, в которых он используется
    for brand in existing_brands:
        # Находим все категории, где используется этот бренд
        categories_with_brand = Category.objects.filter(
            products__brand=brand
        ).distinct()
        
        if categories_with_brand.exists():
            # Присваиваем бренду первую найденную категорию
            first_category = categories_with_brand.first()
            brand.category = first_category
            brand.save()
            
            # Для остальных категорий создаем дубликаты бренда
            for category in categories_with_brand[1:]:
                new_brand = Brand.objects.create(
                    name=brand.name,
                    logo=brand.logo,
                    category=category
                )
                
                # Обновляем товары в этой категории, чтобы они ссылались на новый бренд
                Product.objects.filter(
                    brand=brand,
                    category=category
                ).update(brand=new_brand)
        else:
            # Если бренд не используется ни в одном товаре, 
            # присваиваем ему первую доступную категорию
            first_category = Category.objects.first()
            if first_category:
                brand.category = first_category
                brand.save()


def reverse_populate_brand_categories(apps, schema_editor):
    """
    Обратная операция: объединяем дубликаты брендов
    """
    Brand = apps.get_model('products', 'Brand')
    Product = apps.get_model('products', 'Product')
    
    # Группируем бренды по имени
    brand_names = Brand.objects.values_list('name', flat=True).distinct()
    
    for brand_name in brand_names:
        brands_with_same_name = Brand.objects.filter(name=brand_name)
        
        if brands_with_same_name.count() > 1:
            # Оставляем первый бренд, остальные удаляем
            main_brand = brands_with_same_name.first()
            duplicate_brands = brands_with_same_name.exclude(id=main_brand.id)
            
            # Переносим все товары на основной бренд
            for duplicate_brand in duplicate_brands:
                Product.objects.filter(brand=duplicate_brand).update(brand=main_brand)
                duplicate_brand.delete()
            
            # Убираем категорию у основного бренда
            main_brand.category = None
            main_brand.save()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_add_category_to_brand'),
    ]

    operations = [
        migrations.RunPython(
            populate_brand_categories,
            reverse_populate_brand_categories
        ),
    ] 