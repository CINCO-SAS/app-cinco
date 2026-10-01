from django.conf import settings
from django.db import models
from apps.operaciones.models.actividad_model import Actividad


class Agenda(models.Model):
    """
    Modelo relacional principal para el agendamiento de actividades / OTs en el calendario.
    Mapeado a la tabla `operaciones_agenda` en la base de datos `default`.
    """
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="agendas",
        db_column="actividad_id",
        help_text="Actividad / OT programada en la agenda"
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="agendas_asignadas",
        db_column="responsable_id",
        help_text="Usuario / Técnico asignado para ejecutar la labor"
    )
    fecha_inicio = models.DateField(help_text="Fecha inicial del agendamiento")
    fecha_fin = models.DateField(help_text="Fecha final del agendamiento")
    sede = models.CharField(max_length=50, db_index=True, help_text="Sede operativa (medellin, monteria, etc.)")
    color_hex = models.CharField(max_length=7, default="#66bb6a", help_text="Color corporativo visual en el calendario")
    observacion = models.TextField(blank=True, null=True, help_text="Notas u observaciones del agendamiento")

    # Auditoría estándar y Soft-Delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agendas_eliminadas",
        db_column="deleted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agendas_creadas",
        db_column="created_by"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agendas_actualizadas",
        db_column="updated_by"
    )

    class Meta:
        db_table = "operaciones_agenda"
        ordering = ["fecha_inicio", "id"]
        indexes = [
            models.Index(fields=["sede", "fecha_inicio", "fecha_fin", "is_deleted"], name="idx_agenda_sede_fechas"),
            models.Index(fields=["responsable", "fecha_inicio", "fecha_fin"], name="idx_agenda_responsable_fechas"),
            models.Index(fields=["actividad", "is_deleted"], name="idx_agenda_actividad_del"),
        ]

    def __str__(self):
        return f"Agenda {self.id} - OT: {self.actividad.ot} - Responsable: {self.responsable_id} ({self.fecha_inicio} a {self.fecha_fin})"


# --- Modelos Legacy para lectura opcional de la BD azul ---

class AgendaTrabajo(models.Model):
    """
    Modelo mapeado a la tabla legacy `agenda_trabajos_cinco` en la BD `azul`.
    """
    _database = "azul"

    id = models.AutoField(primary_key=True)
    cedula = models.CharField(max_length=50)
    sede = models.CharField(max_length=50, blank=True, null=True)
    yyyy = models.CharField(max_length=10)
    mes = models.CharField(max_length=10)
    carpeta = models.CharField(max_length=100, blank=True, null=True)
    datos = models.JSONField(blank=True, null=True)
    edit = models.CharField(max_length=50, blank=True, null=True)
    fecha_edit = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "agenda_trabajos_cinco"
        app_label = "operaciones"


class AgendaTecnicoRegistro(models.Model):
    """
    Modelo mapeado a la tabla legacy `agenda_trabajos_cinco_registro` en la BD `azul`.
    """
    _database = "azul"

    id = models.AutoField(primary_key=True)
    cedula = models.CharField(max_length=50, unique=True)
    sede = models.CharField(max_length=50, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    carpeta = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=10, default="1")
    edit = models.CharField(max_length=50, blank=True, null=True)
    fecha_edit = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "agenda_trabajos_cinco_registro"
        app_label = "operaciones"


class InfraestructuraParametros(models.Model):
    """
    Modelo mapeado a la tabla legacy `infraestructura_parametros` en la BD `azul`.
    """
    _database = "azul"

    id = models.AutoField(primary_key=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    carpeta = models.CharField(max_length=100, blank=True, null=True)
    parametros_agenda = models.JSONField(blank=True, null=True)
    edit = models.CharField(max_length=50, blank=True, null=True)
    fecha_edit = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "infraestructura_parametros"
        app_label = "operaciones"
