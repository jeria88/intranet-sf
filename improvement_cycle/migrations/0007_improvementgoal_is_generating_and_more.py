from django.db import migrations, models

def fix_strategic_objectives(apps, schema_editor):
    ImprovementGoal = apps.get_model('improvement_cycle', 'ImprovementGoal')
    for goal in ImprovementGoal.objects.all():
        val = goal.strategic_objectives
        if not val or (isinstance(val, str) and not val.startswith('[')):
            goal.strategic_objectives = '[]'
            goal.save()

class Migration(migrations.Migration):

    dependencies = [
        ('improvement_cycle', '0006_improvementgoal_associated_booking_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_strategic_objectives),
        migrations.AddField(
            model_name='improvementgoal',
            name='is_generating',
            field=models.BooleanField(default=False, verbose_name='IA Redactando'),
        ),
        migrations.AlterField(
            model_name='improvementgoal',
            name='strategic_objectives',
            field=models.JSONField(blank=True, default=list, verbose_name='Objetivos Estratégicos'),
        ),
        migrations.AlterField(
            model_name='improvementgoal',
            name='subvention_type',
            field=models.CharField(choices=[('SEP', 'SEP'), ('PIE', 'PIE'), ('MANTENCION', 'Mantención'), ('PRO_RETENCION', 'Pro-Retención'), ('NO_CORRESPONDE', 'No corresponde'), ('OTRO', 'Otro')], default='SEP', max_length=20, verbose_name='Tipo de Subvención'),
        ),
    ]
