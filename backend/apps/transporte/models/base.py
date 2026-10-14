"""
Bases del módulo Transporte.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.A (D-A5).
"""
from django.conf import settings
from django.db import models


class AuditoriaModel(models.Model):
    """
    Auditoría estándar del módulo (D-A5).

    Reemplaza los `edit`/`fecha_edit` "a medias" de las 3 tablas legacy
    (transportadores_vehiculos, transporte_registro_salida,
    transporte_base_conductores).
    """

    creado_por = models.ForeignKey(
        "empleados.Empleado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_creados",
        # Cross-database (transporte=default, empleados=azul): el router
        # MultiDBRouter resuelve la lectura; el constraint de BD no aplica (D-A10).
        db_constraint=False,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_por = models.ForeignKey(
        "empleados.Empleado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_modificados",
        db_constraint=False,
    )
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
