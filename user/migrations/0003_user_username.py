# Generated by Django 4.1.7 on 2023-07-06 11:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_alter_user_managers_remove_user_username_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, null=True),
        ),
    ]
