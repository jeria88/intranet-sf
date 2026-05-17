from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('calendar_red', '0003_calendarevent_deleted_at_calendarevent_deleted_by_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoCultural',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título')),
                ('descripcion', models.TextField(verbose_name='Descripción')),
                ('tipo', models.CharField(choices=[('cultural', 'Cultural'), ('deportivo', 'Deportivo')], default='cultural', max_length=15, verbose_name='Tipo')),
                ('fecha', models.DateField(verbose_name='Fecha')),
                ('hora', models.TimeField(blank=True, null=True, verbose_name='Hora')),
                ('lugar', models.CharField(max_length=200, verbose_name='Lugar')),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='eventos/', verbose_name='Imagen/Afiche')),
                ('status', models.CharField(choices=[('borrador', 'Borrador'), ('publicado', 'Publicado'), ('finalizado', 'Finalizado')], default='borrador', max_length=15, verbose_name='Estado')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('calendar_event', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evento_cultural', to='calendar_red.calendarevent')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_culturales', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Evento Cultural/Deportivo',
                'verbose_name_plural': 'Eventos Culturales/Deportivos',
                'ordering': ['-fecha'],
            },
        ),
    ]
