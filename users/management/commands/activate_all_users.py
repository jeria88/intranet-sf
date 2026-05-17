from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

ESTABLISHMENTS = [
    'TEMUCO', 'LAUTARO', 'RENAICO', 'SANTIAGO',
    'IMPERIAL', 'ERCILLA', 'ARAUCO', 'ANGOL',
]

ROLES = [
    'DIRECTOR',
    'UTP',
    'INSPECTOR',
    'CONVIVENCIA',
    'REPRESENTANTE',
]

DEFAULT_PASSWORD = 'Admin1234!'


class Command(BaseCommand):
    help = 'Crea/activa todos los usuarios de todos los establecimientos con nombre en blanco.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        all_combos = [(role, ee) for ee in ESTABLISHMENTS for role in ROLES]
        # Equipo Red
        all_combos.append(('RED', 'RED'))

        for role, ee in all_combos:
            username = f"{role.lower()}.{ee.lower()}"

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'role': role,
                    'establishment': ee,
                    'email': f"{username}@intranet-sfa.cl",
                    'is_active': True,
                    'first_name': '',
                    'last_name': '',
                }
            )

            changed = False

            if not user.is_active:
                user.is_active = True
                changed = True

            # Limpiar nombre de todos excepto UTP Temuco
            if username == 'utp.temuco':
                if user.first_name != 'Luis Humberto' or user.last_name != 'Jeria Castro':
                    user.first_name = 'Luis Humberto'
                    user.last_name = 'Jeria Castro'
                    changed = True
            else:
                if user.first_name or user.last_name:
                    user.first_name = ''
                    user.last_name = ''
                    changed = True

            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                created_count += 1
                self.stdout.write(f'  CREADO   {username}')
            elif changed:
                user.save()
                updated_count += 1
                self.stdout.write(f'  ACTUALIZADO {username}')
            else:
                self.stdout.write(self.style.SUCCESS(f'  OK       {username}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Completado: {created_count} creados, {updated_count} actualizados.'
        ))
        self.stdout.write(f'Contraseña por defecto: {DEFAULT_PASSWORD}')
        self.stdout.write('Recuerda que cada usuario debe cambiar su nombre al ingresar.')
