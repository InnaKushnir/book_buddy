# Generated by Django 4.1.7 on 2023-02-25 07:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0011_borrowing_is_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="borrowing",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]