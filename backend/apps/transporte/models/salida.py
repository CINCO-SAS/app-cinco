"""
Modelos transaccionales de Salidas (el corazón del módulo, ~201k filas legacy).

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.C.
Legacy: transporte_registro_salida (11 columnas + JSON `datos` + longtext `historial`).
"""
from django.db import models

from apps.empleados.models import Empleado

from .base import AuditoriaModel
from .choices import EstadoSalida, TipoNovedad
from .vehiculo import Conductor, Vehiculo


class Salida(AuditoriaModel):
    """
    Registro de salida de una móvil. Reemplaza sentinellas 'disponible'/'0'
    de `movil_sale` por FK nullable + flag `es_disponible`.

    CR-1/CR-2 + D-A12: la unicidad (vehiculo, fecha) y (conductor, fecha) es
    CONTRA SALIDAS VIVAS (estado != 'ELIMINADO'); el legacy permitía registrar
    otra salida el mismo día tras un borrado lógico. MySQL 8 no soporta unique
    parcial declarativo en el ORM: se implementará como columna virtual
    STORED + UNIQUE en una migración SQL (pendiente de la auditoría §7.1).
    """
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="salidas"
    )
    fecha_salida = models.DateField(db_index=True)
    # Quien SALE (legacy movil_sale); conductor externo autónomo.
    conductor = models.ForeignKey(
        Conductor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="salidas",
    )
    # Móvil ASIGNADA al vehículo (legacy cedula_tecnico): personal de nómina.
    tecnico_asignado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="salidas_como_movil",
        db_constraint=False,  # cross-database (empleados vive en 'azul')
    )
    es_disponible = models.BooleanField(default=False)
    # TODO(F0/ETL): convertir en FK a common.Area (CR-5: nullable por carga
    # histórica; el área vive en el JSON `datos` y puede faltar). Mientras, snapshot.
    area = models.CharField(max_length=100, null=True, blank=True)
    carpeta = models.CharField(max_length=100, null=True, blank=True)
    sede = models.CharField(max_length=100, null=True, blank=True)
    # SNAPSHOT inmutable de la tarifa al momento de salir.
    valor_dia = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(
        max_length=20,
        choices=EstadoSalida.choices,
        default=EstadoSalida.REPORTADO,
        db_index=True,
    )
    observacion = models.TextField(blank=True)
    # Badge Reporte SI/NO (legacy datos.reporte/reportes_adicionales).
    reportado = models.BooleanField(default=False)

    class Meta:
        db_table = "transporte_salida"
        verbose_name = "Salida"
        verbose_name_plural = "Salidas"
        # Permisos granulares que reemplazan las cédulas hardcodeadas del
        # legacy (CR-8 / §5.9). Se leen vía PermisoService (E3).
        permissions = [
            ("puede_programar", "Programación (reemplaza $permi_programacion)"),
            ("permiso_especial", "Permiso especial (reemplaza permi_especial)"),
            ("editar_tras_cierre", "Editar tras cierre (reemplaza permi_editar_fecha)"),
        ]
        # TODO(D-A12 + §7.1): tras auditoría de duplicados históricos, añadir
        # UNIQUE vía columna virtual STORED ~Q(estado='ELIMINADO') para
        # (vehiculo, fecha_salida) y (conductor, fecha_salida) [CR-1, CR-2].
        indexes = [
            models.Index(fields=["fecha_salida", "estado"]),
            models.Index(fields=["area", "fecha_salida"]),
        ]

    def __str__(self):
        return f"#{self.pk} {self.vehiculo_id} {self.fecha_salida} [{self.estado}]"

    @property
    def total_a_pagar(self):
        """valor_dia ± novedad — implementación única determinista (§5.1)."""
        novedad = getattr(self, "novedad", None)
        if not novedad:
            return self.valor_dia
        if novedad.tipo == TipoNovedad.ADICIONAL:
            return self.valor_dia + novedad.valor
        return self.valor_dia - novedad.valor


class SalidaHistorial(AuditoriaModel):
    """
    Trazabilidad 1:N de cambios de estado. Reemplaza el JSON `historial`
    longtext del legacy (§7.2: se desempaquetará en la ETL).
    """
    salida = models.ForeignKey(
        Salida, on_delete=models.CASCADE, related_name="historial"
    )
    estado = models.CharField(max_length=20, choices=EstadoSalida.choices)
    # Obligatorio en RECHAZADO (verificado: rechazar_salida exige motivo).
    motivo = models.TextField(blank=True)
    fecha_cambio = models.DateTimeField()

    class Meta:
        db_table = "transporte_salida_historial"
        verbose_name = "Historial de salida"
        verbose_name_plural = "Historiales de salidas"
        ordering = ["-fecha_cambio"]


class Novedad(AuditoriaModel):
    """
    Novedad de la salida (ADICIONAL/DESCUENTO). UNA por salida: el legacy
    sobrescribía el JSON `datos.novedad`; aquí se preserva el comportamiento
    con OneToOne (§3.C).
    """
    salida = models.OneToOneField(
        Salida, on_delete=models.CASCADE, related_name="novedad"
    )
    tipo = models.CharField(max_length=20, choices=TipoNovedad.choices)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion = models.TextField()

    class Meta:
        db_table = "transporte_novedad"
        verbose_name = "Novedad"
        verbose_name_plural = "Novedades"

    def __str__(self):
        return f"{self.tipo} ${self.valor} — salida #{self.salida_id}"
