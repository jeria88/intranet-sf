from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simce', '0003_modo_sesion'),
    ]

    operations = [
        migrations.AddField(
            model_name='textoprueba',
            name='word_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Palabras'),
        ),
        migrations.AddField(
            model_name='textoprueba',
            name='dificultad',
            field=models.PositiveSmallIntegerField(
                choices=[(1, 'Básico'), (2, 'Intermedio'), (3, 'Avanzado')],
                default=2,
                verbose_name='Dificultad del texto',
            ),
        ),
        migrations.AddField(
            model_name='textoprueba',
            name='estado_texto',
            field=models.CharField(
                choices=[('pendiente', 'Pendiente'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')],
                default='pendiente',
                max_length=10,
                verbose_name='Estado revisión',
            ),
        ),
        migrations.AddField(
            model_name='textoprueba',
            name='checklist_admin',
            field=models.JSONField(default=dict, verbose_name='Checklist admin'),
        ),
        migrations.AlterField(
            model_name='prueba',
            name='estado',
            field=models.CharField(
                choices=[
                    ('generando',           'Generando…'),
                    ('generando_textos',    'Generando textos…'),
                    ('revision_textos',     'Revisando textos'),
                    ('generando_preguntas', 'Generando preguntas…'),
                    ('borrador',            'Borrador'),
                    ('error',               'Error de generación'),
                    ('revision',            'En Revisión'),
                    ('aprobada',            'Aprobada'),
                    ('publicada',           'Publicada'),
                    ('cerrada',             'Cerrada'),
                ],
                default='borrador',
                max_length=22,
            ),
        ),
    ]
