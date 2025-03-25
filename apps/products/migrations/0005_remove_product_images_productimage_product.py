# Generated by Django 4.2.10 on 2025-03-25 23:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_category_slug"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="images",
        ),
        migrations.AddField(
            model_name="productimage",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="images",
                to="products.product",
                verbose_name="product",
            ),
        ),
    ]
