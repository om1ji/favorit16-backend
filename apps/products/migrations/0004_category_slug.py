# Generated by Django 4.2.10 on 2025-03-23 21:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "products",
            "0003_brand_product_diameter_product_profile_product_width_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text="URL-friendly name, must be unique",
                max_length=255,
                null=True,
                unique=True,
                verbose_name="slug",
            ),
        ),
    ]
