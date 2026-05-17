from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class EncuestaSemana(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='encuestas')
    iso_year = models.IntegerField()
    iso_week = models.IntegerField()

    p1_score = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    p1_comentario = models.TextField(blank=True)
    p2_score = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    p2_comentario = models.TextField(blank=True)
    p3_score = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    p3_comentario = models.TextField(blank=True)
    p4_score = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    p4_comentario = models.TextField(blank=True)
    p5_score = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    p5_comentario = models.TextField(blank=True)

    respondida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'iso_year', 'iso_week')
        ordering = ['-iso_year', '-iso_week']

    def __str__(self):
        return f"{self.user} – Semana {self.iso_week}/{self.iso_year}"

    def promedio(self):
        return round((self.p1_score + self.p2_score + self.p3_score + self.p4_score + self.p5_score) / 5, 2)
