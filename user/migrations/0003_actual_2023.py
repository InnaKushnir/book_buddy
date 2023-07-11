from django.db import migrations
from django.core.management import call_command


def load_fixture(apps, schema_editor):
    call_command("loaddata", "db.json")


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0002_user_username"),
    ]
    operations = [
        migrations.RunPython(load_fixture, reverse_func),
    ]
