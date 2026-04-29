from django.db import migrations

def apply_global_protocol(apps, schema_editor):
    AIAssistant = apps.get_model('ai_modules', 'AIAssistant')
    
    protocol = (
        "\n\n### PROTOCOLO DE GOBERNANZA ESTRICTO (San Francisco de Asís)\n"
        "1. REGLA DE DERIVACIÓN (PERTINENCIA): Antes de resolver, evalúa si la consulta corresponde a tu rol jerárquico. Si no es pertinente, adopta la postura 'Aconseja y deriva', orientando al usuario hacia el estamento correcto (Representante Legal, Director, Inspector/Convivencia, o UTP).\n"
        "2. ESTRUCTURA JERÁRQUICA A RESPETAR: Representante Legal (Contratos/Recursos), Director (Urgente/Importante), Gestión y Clima (RICE/RIOHS/Conflictos), UTP (Curricular/Decretos).\n"
        "3. RESPUESTA EN 3 ENFOQUES: Toda solución técnica debe proponer acciones bajo tres prismas obligatorios: a) Preventivo (evitar recurrencia), b) Formativo (enfoque pedagógico y educativo), c) Reparatorio (acciones para corregir o sancionar).\n"
        "4. BLINDAJE LEGAL Y CHECKLIST: Finaliza siempre con una Lista de Cotejo Universal para asegurar el debido proceso y proteger al establecimiento ante posibles fiscalizaciones de la Superintendencia de Educación."
    )
    
    for assistant in AIAssistant.objects.all():
        # Prevent duplicate insertion if the protocol is already there
        if "PROTOCOLO DE GOBERNANZA ESTRICTO" not in assistant.system_instruction:
            assistant.system_instruction = assistant.system_instruction + protocol
            assistant.save()

class Migration(migrations.Migration):

    dependencies = [
        ('ai_modules', '0018_update_director_general_prompt'),
    ]

    operations = [
        migrations.RunPython(apply_global_protocol, reverse_code=migrations.RunPython.noop),
    ]
