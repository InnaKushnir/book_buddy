# Generated by Django 4.1.7 on 2023-06-22 08:36

from django.db import migrations


def load_fixture(apps, schema_editor):
    from django.core.management import call_command

    call_command("loaddata", "db.json")


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0017_alter_payment_session_id_alter_payment_session_url"),
    ]

    operations = [
        migrations.RunPython(load_fixture, reverse_func),
    ]
