"""
Modelos de liquidaciones, cierres y parámetros del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.D.
Legacy: transporte_registro_salida_fechas_limites, consecutivos_mensuales,
transporte_validacion_salidas, programacion_parametros (JSON de jefes).
"""
from django.db import models

from apps.empleados.models import Empleado

from .base import AuditoriaModel
from .choices import TipoPago
from .vehiculo import Vehiculo


class FechaLimiteCierre(AuditoriaModel):
    """
    Fecha límite de edición del cierre mensual.
    Legacy transporte_registro_salida_fechas_limites (ON DUPLICATE KEY → UNIQUE).
    """
    mes = models.PositiveSmallIntegerField()
    anio = models.PositiveIntegerField()
    fecha_limite = models.DateField()

    class Meta:
        db_table = "transporte_fecha_limite_cierre"
        verbose_name = "Fecha límite de cierre"
        verbose_name_plural = "Fechas límite de cierre"
        constraints = [
            models.UniqueConstraint(
                fields=["mes", "anio"], name="uq_cierre_mes_anio"
            )
        ]

    def __str__(self):
        return f"{self.mes:02d}/{self.anio} → {self.fecha_limite}"


class ConsecutivoMensual(AuditoriaModel):
    """
    Consecutivo mensual por vehículo (planilla de salida).
    Legacy consecutivos_mensuales. La generación usa select_for_update()
    en LiquidacionService para erradicar la condición de carrera MAX+1.
    """
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="consecutivos"
    )
    mes = models.PositiveSmallIntegerField()
    anio = models.PositiveSmallIntegerField()
    consecutivo = models.PositiveIntegerField()

    class Meta:
        db_table = "transporte_consecutivo_mensual"
        verbose_name = "Consecutivo mensual"
        verbose_name_plural = "Consecutivos mensuales"
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo", "mes", "anio"], name="uq_consecutivo_periodo"
            )
        ]


class PagoVehiculoMensual(AuditoriaModel):
    """
    Marca de liquidación/pago mensual o pronto pago por vehículo.
    Desempaquetado del JSON legacy datos.pago_mensual[] / pronto_pago[].
    """
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.CASCADE, related_name="pagos"
    )
    mes = models.PositiveSmallIntegerField()
    anio = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=20, choices=TipoPago.choices)
    pagado = models.BooleanField(default=False)
    fecha_pago = models.DateField(null=True, blank=True)
    # Snapshot del cálculo al momento de liquidar.
    total_liquidado = models.DecimalField(
        max_digits=14, decimal_places=2, default=0
    )

    class Meta:
        db_table = "transporte_pago_vehiculo"
        verbose_name = "Pago de vehículo"
        verbose_name_plural = "Pagos de vehículos"
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo", "mes", "anio", "tipo"],
                name="uq_pago_periodo_tipo",
            )
        ]

    def __str__(self):
        return f"{self.vehiculo} {self.get_tipo_display()} {self.mes:02d}/{self.anio}"


class JefeValidador(AuditoriaModel):
    """
    Jefes validadores por área/carpeta (reemplaza el JSON de
    programacion_parametros). Verificado en isUserLeaderOfSalida.
    """
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name="validaciones_transporte",
        db_constraint=False,  # cross-database (empleados vive en 'azul')
    )
    # TODO(common.Area): convertir en ManyToManyField a common.Area cuando
    # exista el modelo (decidido posponer; viene de otro archivo PHP).
    areas = models.JSONField(default=list, blank=True)
    carpetas_por_area = models.JSONField(default=dict, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "transporte_jefe_validador"
        verbose_name = "Jefe validador"
        verbose_name_plural = "Jefes validadores"

    def __str__(self):
        return f"Jefe validador #{self.empleado_id}"


class ValidacionSalida(AuditoriaModel):
    """
    Cierre mensual de validación de salidas por área.
    Legacy transporte_validacion_salidas (JSON datos).
    """
    # TODO(common.Area): convertir en FK a common.Area (mismo motivo que JefeValidador).
    area = models.CharField(max_length=100)
    mes = models.PositiveSmallIntegerField()
    anio = models.PositiveSmallIntegerField()
    datos = models.JSONField(default=dict)

    class Meta:
        db_table = "transporte_validacion_salida"
        verbose_name = "Validación de salida"
        verbose_name_plural = "Validaciones de salidas"
        constraints = [
            models.UniqueConstraint(
                fields=["area", "mes", "anio"], name="uq_validacion_area_periodo"
            )
        ]
