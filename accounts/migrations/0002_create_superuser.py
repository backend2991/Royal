from django.db import migrations

def create_superuser(apps, schema_editor):
    User = apps.get_model('accounts', 'AdminUser')
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='AdminPassword123!'  # Admin parolini shu yerga yozing
        )

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),  # Oxirgi migration faylingiz nomi
    ]

    operations = [
        migrations.RunPython(create_superuser),
    ]