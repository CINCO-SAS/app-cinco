"""
F5-5 · Validación WFM masiva.

Port de `transporte_validacion_wfm_service.php` (836 L) y su worker.

Tres piezas:

1. ``WfmJob`` — la cola de trabajos (``transporte_validacion_wfm_jobs``).
   Tabla del propio módulo (transporte → DB ``default``), creada por
   migración. Es estado **transitorio** de una cola interna, así que no
   hay queja de compatibilidad al cutover: el legado la escribía con
   estados en minúscula y aquí se usan mayúsculas (D-A6, decisión del
   módulo) — la cola vacía al cutover.

2. ``ResidencialWfm`` — ``residencial_base_wfm`` (BD ``azul``, **solo
   lectura**, módulo residencial). Fuente primaria de "¿la persona
   estuvo en WFM ese día?".

3. ``AgendaLogistica`` — ``logistica_actividades_modulo_agenda``
   (BD ``azul``, **solo lectura**, módulo logística). Respaldo cuando no
   hay NINGÚN registro WFM ese día.

Los dos últimos son ``managed=False`` con ``_database = "azul"``, igual
que ``empleados.Empleado``: el ``MultiDBRouter`` los enruta a la BD
ajena y Django no les genera migración. Regla del proyecto: módulos
ajenos **nunca se editan**, solo se leen (§R3).
"""
from django.db import models


class EstadoWfmJob(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PROCESANDO = "PROCESANDO", "Procesando"
    COMPLETADO = "COMPLETADO", "Completado"
    ERROR = "ERROR", "Error"


class WfmJob(models.Model):
    """
    Cola de validación WFM (``transporte_validacion_wfm_jobs`` legacy).

    Se procesa día a día (``chunkDays``) con ``fecha_cursor`` como marca
    de agua: si un lote no se vacía (``has_more_in_chunk``) el cursor no
    avanza y se reintenta, de forma idempotente.
    """

    job_uuid = models.CharField(max_length=32, unique=True)
    estado = models.CharField(
        max_length=12,
        choices=EstadoWfmJob.choices,
        default=EstadoWfmJob.PENDIENTE,
        db_index=True,
    )
    area = models.CharField(max_length=100, default="TODAS")
    mes = models.PositiveSmallIntegerField(default=0)
    yyyy = models.PositiveSmallIntegerField(default=0)
    # `fecha_fin` es INCLUSIVA en la cola (el rango semiabierto del
    # servicio se convierte al guardarlo), igual que el legado.
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_cursor = models.DateField(null=True, blank=True)
    total_dias = models.PositiveIntegerField(default=1)
    dias_procesados = models.PositiveIntegerField(default=0)
    total_reportados = models.PositiveIntegerField(default=0)
    total_validados = models.PositiveIntegerField(default=0)
    mensaje = models.CharField(max_length=255, blank=True, default="")
    detalle_error = models.TextField(null=True, blank=True)
    # El legado guarda la CÉDULA como texto (no una FK): se respeta
    # para no atar la cola a empleados.Empleado (BD ajena, cross-db).
    creado_por = models.CharField(max_length=50, blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.CharField(max_length=120, blank=True, default="")
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "transporte_validacion_wfm_jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["estado", "area", "mes", "yyyy"],
                name="idx_wfm_job_cola",
            ),
        ]

    def __str__(self):
        return f"WfmJob {self.job_uuid} [{self.estado}]"


class ResidencialWfm(models.Model):
    """
    ``residencial_base_wfm`` — **solo lectura** (módulo residencial, azul).

    Marca que una cédula (``external_id`` / ``cc_auxiliar``) tuvo actividad
    WFM en ``fecha``. No se modelan sus columnas de estado: el legado
    solo pregunta "¿existe algún registro ese día?" (ver hallazgo en
    ``WfmService``: los mapas "completado" y "any" se poblaban
    idénticamente, así que la distinción era vestigial).
    """

    _database = "azul"

    id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=50, blank=True, null=True)
    cc_auxiliar = models.CharField(max_length=50, blank=True, null=True)
    fecha = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "residencial_base_wfm"
        app_label = "transporte"


class AgendaLogistica(models.Model):
    """
    ``logistica_actividades_modulo_agenda`` — **solo lectura** (azul).

    Respaldo del WFM: si una persona NO tiene ningún registro WFM ese
    día, basta con que aparezca en la agenda por ``cedula`` o por
    ``movil``, ya sea por ``fecha`` o por ``fecha_cierre``.
    """

    _database = "azul"

    id = models.AutoField(primary_key=True)
    cedula = models.CharField(max_length=50, blank=True, null=True)
    movil = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField(blank=True, null=True)
    fecha_cierre = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "logistica_actividades_modulo_agenda"
        app_label = "transporte"
