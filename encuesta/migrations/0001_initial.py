from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EncuestaSemana',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iso_year', models.IntegerField()),
                ('iso_week', models.IntegerField()),
                ('p1_score', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('p1_comentario', models.TextField(blank=True)),
                ('p2_score', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('p2_comentario', models.TextField(blank=True)),
                ('p3_score', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('p3_comentario', models.TextField(blank=True)),
                ('p4_score', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('p4_comentario', models.TextField(blank=True)),
                ('p5_score', models.SmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('p5_comentario', models.TextField(blank=True)),
                ('respondida_en', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='encuestas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-iso_year', '-iso_week'],
                'unique_together': {('user', 'iso_year', 'iso_week')},
            },
        ),
    ]
