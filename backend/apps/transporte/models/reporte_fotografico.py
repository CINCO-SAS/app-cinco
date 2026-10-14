"""
Reporte fotográfico diario de vehículos.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.D.
Alcance nuevo del plan 2026; archivo legacy transporte_reporte_vehiculo_inc.php
aún no verificado (pendiente P1). Reglas provisorias: agenda en
operaciones_agenda, ventana 10:00–16:00 (Bogotá), compresión Pillow.
"""
from django.db import models

from apps.empleados.models import Empleado

from .base import AuditoriaModel
from .vehiculo import Vehiculo


class ReporteFotograficoVehiculo(AuditoriaModel):
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="reportes_fotos"
    )
    responsable = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="reportes_fotos_creados",
        db_constraint=False,  # cross-database (empleados vive en 'azul')
    )
    fecha = models.DateField()
    hora = models.TimeField()
    ot_actividad = models.CharField(max_length=100, null=True, blank=True)
    imagen = models.ImageField(
        upload_to="transporte/reportes_diarios/%Y/%m/%d/"
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "transporte_reporte_fotografico"
        verbose_name = "Reporte fotográfico de vehículo"
        verbose_name_plural = "Reportes fotográficos de vehículos"
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo", "fecha"],
                name="uq_reporte_foto_vehiculo_dia",
            )
        ]

    def __str__(self):
        return f"{self.vehiculo} {self.fecha} {self.hora}"
