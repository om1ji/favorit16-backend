# Generated by Django 4.2.10 on 2025-02-21 11:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="category",
            name="slug",
        ),
        migrations.RemoveField(
            model_name="product",
            name="slug",
        ),
    ]
