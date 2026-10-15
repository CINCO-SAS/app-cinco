"""
Reporte fotográfico diario de vehículos.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.D.
Legacy verificado (P1 resuelto): transporte_reporte_vehiculo_inc.php (frontend/
reglas) y controlador_transporte_img_reporte_salida_fix.php (agenda, exenciones,
save `guardar_img_reporte_vehiculo`).

Paridad legacy conservada:
- **1 a 5 imágenes** por reporte (límite superior del frontend).
- **Un reporte por (vehículo, fecha, técnico)**: el legacy distinguía
  ``datos.reporte`` (técnico principal) y ``reportes_adicionales[]`` (otros
  técnicos el mismo día para el mismo vehículo). Aquí se normaliza a filas:
  cada técnico aporta su propia fila, y las 1..5 imágenes viven en una tabla
  hija (no en JSON embebido — §7.2 elimina la persistencia en JSON).
- ``ot_actividad`` + ``validacion_ot`` (blob de la validación OT, snapshot
  puntual) y ``location`` (georreferencia del móvil) como JSONField: son
  datos genuinamente anidados de solo lectura/auditoría, no relaciones.

Mejoras sobre el legacy (ver services/reporte_fotografico_service.py):
- La ventana y el gate de agenda se validan en SERVIDOR (el legacy solo en JS).
- La identidad del responsable NO viene del cliente (``dni`` doble-base64).
"""
from django.db import models

from apps.empleados.models import Empleado

from .base import AuditoriaModel
from .vehiculo import Vehiculo


class ReporteFotograficoVehiculo(AuditoriaModel):
    """Un reporte diario de un técnico sobre un vehículo (1 fila por técnico)."""

    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="reportes_fotos"
    )
    # El técnico responsable se deriva del usuario autenticado (no del cliente).
    responsable = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="reportes_fotos_creados",
        db_constraint=False,  # cross-database (empleados vive en 'azul')
    )
    fecha = models.DateField(db_index=True)
    hora = models.TimeField()
    ot_actividad = models.CharField(max_length=100, null=True, blank=True)
    # Snapshot de la validación OT (transporteOmiteValidacionOt /
    # validarOtActividadTransporte): éxito, ventana de la OT, estado, etc.
    validacion_ot = models.JSONField(default=dict, blank=True)
    # Georreferencia enviada por el móvil (lat/lon/precisión/opcional).
    location = models.JSONField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "transporte_reporte_fotografico"
        verbose_name = "Reporte fotográfico de vehículo"
        verbose_name_plural = "Reportes fotográficos de vehículos"
        constraints = [
            # Regla de duplicado legacy: mismo técnico no repite reporte para
            # el mismo vehículo en la misma fecha; otro técnico sí puede sumar.
            models.UniqueConstraint(
                fields=["vehiculo", "fecha", "responsable"],
                name="uq_reporte_foto_veh_fecha_tec",
            )
        ]
        indexes = [
            models.Index(
                fields=["fecha", "vehiculo"], name="idx_reporte_foto_fecha_veh"
            ),
        ]

    def __str__(self):
        return f"{self.vehiculo} {self.fecha} {self.hora}"


class ReporteFotoImagen(AuditoriaModel):
    """
    Imagen individual de un reporte (1 a 5 por reporte).

    El legacy guardaba ``datos.reporte.imagenes[]`` (rutas en texto) dentro de
    la fila de salida; aquí cada imagen es una fila consultable y con
    auditoría. La compresión (Pillow, 1280px/q0.7) se aplica al guardar.
    """

    reporte = models.ForeignKey(
        ReporteFotograficoVehiculo, on_delete=models.CASCADE, related_name="imagenes"
    )
    imagen = models.ImageField(
        upload_to="transporte/reportes_diarios/%Y/%m/%d/"
    )
    nombre_original = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "transporte_reporte_foto_imagen"
        verbose_name = "Imagen de reporte fotográfico"
        verbose_name_plural = "Imágenes de reportes fotográficos"

    def __str__(self):
        return f"{self.reporte_id} — {self.nombre_original or self.imagen.name}"
