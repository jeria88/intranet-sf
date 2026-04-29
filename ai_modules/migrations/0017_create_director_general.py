from django.db import migrations

def create_director_general(apps, schema_editor):
    AIAssistant = apps.get_model('ai_modules', 'AIAssistant')
    
    AIAssistant.objects.get_or_create(
        slug='director-general',
        defaults={
            'name': 'Asistente Director General',
            'profile_role': 'DIRECTOR',
            'establishment': '',  # General
            'is_active': True,
            'is_chat_enabled': True,
            'description': 'Asistente estratégico centralizado para todos los directores.',
            'system_instruction': (
                "Área de Acción: Universal (aplica a cualquier situación de dirección).\n"
                "Funciones: Gestionar lo Urgente/Importante, delegar liderazgo, monitorear procesos.\n"
                "Foco: Aseguramiento de calidad, gestión institucional y normativa."
            )
        }
    )

def remove_director_general(apps, schema_editor):
    AIAssistant = apps.get_model('ai_modules', 'AIAssistant')
    AIAssistant.objects.filter(slug='director-general').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('ai_modules', '0016_remove_aiassistant_notebook_url'),
    ]

    operations = [
        migrations.RunPython(create_director_general, remove_director_general),
    ]
