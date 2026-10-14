"""
Log de auditoría del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.D.
Legacy transporte_log (acumula cambios).
"""
from django.db import models

from .base import AuditoriaModel


class AuditoriaLog(AuditoriaModel):
    tabla = models.CharField(max_length=60)
    accion = models.CharField(max_length=20)
    registro_id = models.IntegerField()
    datos_antes = models.JSONField(null=True, blank=True)
    datos_despues = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "transporte_auditoria_log"
        verbose_name = "Log de auditoría"
        verbose_name_plural = "Logs de auditoría"

    def __str__(self):
        return f"{self.accion} {self.tabla}#{self.registro_id}"
