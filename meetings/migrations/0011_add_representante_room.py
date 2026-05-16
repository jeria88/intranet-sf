from django.db import migrations


def add_representante_room(apps, schema_editor):
    MeetingRoom = apps.get_model('meetings', 'MeetingRoom')
    MeetingRoom.objects.get_or_create(
        slug='representante-legal',
        defaults={
            'name': 'Sala Representante Legal',
            'description': 'Sala de videollamadas para el Representante Legal',
            'room_type': 'daily',
            'daily_identifier': 'representante-legal',
            'target_role': 'REPRESENTANTE',
            'target_establishment': '',
            'allowed_roles': [],
            'is_unlimited': False,
        }
    )


def remove_representante_room(apps, schema_editor):
    MeetingRoom = apps.get_model('meetings', 'MeetingRoom')
    MeetingRoom.objects.filter(slug='representante-legal').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0010_add_recording_r2_url'),
    ]

    operations = [
        migrations.RunPython(add_representante_room, remove_representante_room),
    ]
