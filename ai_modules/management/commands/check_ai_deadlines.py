from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_modules.models import AIQuery
from improvement_cycle.models import RiskAlert


class Command(BaseCommand):
    help = 'Marca como vencidas las consultas IA que superaron el plazo de 24 horas.'

    def handle(self, *args, **options):
        now = timezone.now()
        overdue = AIQuery.objects.filter(
            deadline__lt=now,
            status__in=['pendiente', 'en_proceso']
        )
        count = overdue.count()
        if count:
            overdue.update(status='vencida')
            # Crear alerta de riesgo para cada una
            for q in AIQuery.objects.filter(deadline__lt=now, status='vencida'):
                RiskAlert.objects.get_or_create(
                    alert_type='consulta_ia_vencida',
                    description=f'Consulta de {q.user} a {q.assistant.name} vencida sin respuesta.',
                    defaults={
                        'affected_establishments': [q.user.establishment],
                        'related_object_info': f'AIQuery #{q.pk}',
                    }
                )
            self.stdout.write(self.style.WARNING(f'{count} consulta(s) marcada(s) como vencidas.'))
        else:
            self.stdout.write(self.style.SUCCESS('Sin consultas vencidas.'))
