# Generated by Django 5.2.1 on 2025-06-23 13:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Eatify', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Eatify.address'),
        ),
        migrations.AlterField(
            model_name='foodmetainformation',
            name='food_measure',
            field=models.CharField(blank=True, choices=[('GM', 'GM'), ('KG', 'KG'), ('ML', 'ML'), ('L', 'L')], max_length=100, null=True),
        ),
    ]
