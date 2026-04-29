from django.db import migrations
from django.contrib.auth.hashers import make_password

def set_director_admin_password(apps, schema_editor):
    User = apps.get_model('users', 'User')
    # Aseguramos que el usuario exista y tenga la contraseña correcta
    u, created = User.objects.get_or_create(
        username='director.admin',
        defaults={
            'role': 'DIRECTOR',
            'establishment': 'RED',
            'is_staff': False,
            'is_active': True,
        }
    )
    u.password = make_password('Admin.1234')
    # Nos aseguramos de que el rol sea el correcto por si ya existía con otro
    u.role = 'DIRECTOR'
    u.establishment = 'RED'
    u.save()

def reverse_password(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('ai_modules', '0020_ensure_director_admin_permissions'),
    ]

    operations = [
        migrations.RunPython(set_director_admin_password, reverse_password),
    ]
