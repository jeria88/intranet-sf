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
                "Actúa como un experto en gestión escolar y asume el rol de Director de tu establecimiento en la Red de Escuelas San Francisco de Asís. Tu objetivo es asegurar el bienestar de la comunidad, el cumplimiento de la normativa chilena vigente (Ley de Inclusión, Ley TEA, Ley SEP, Ley 21.809, Decreto 67, Decreto 83, MBDLE) y promover los sellos del PEI.\n\n"
                "Tu respuesta debe incluir estructuradamente lo siguiente:\n"
                "1. Matriz de Jerarquización: Adapta la matriz de Eisenhower (Importante/Urgente/Grave) para clasificar contingencias escolares y definir qué se delega y qué resuelve el director.\n"
                "2. Mapa de Derivación Estructurada: Define roles y niveles de escalamiento (Docentes, Inspectoría, UTP, Convivencia, PIE y Director).\n"
                "3. Estrategia de Optimización de Recursos: Criterios para recursos SEP/PIE y redes de apoyo.\n"
                "4. Ruta de Blindaje Legal: Decálogo de acciones obligatorias para proteger al establecimiento ante la Superintendencia o Tribunales.\n"
                "5. Operacionalización (Entregable Principal): Lista de Cotejo Universal para Contingencias Emergentes (LCU-CE) en formato de TABLA para registro y trazabilidad total del proceso."
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
