# Generated manually to make brand category field required

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_populate_brand_categories'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brand',
            name='category',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='brands',
                to='products.category',
                verbose_name='category'
            ),
        ),
    ] 