"""
ValidacionService — cierre mensual de validación de salidas por área.

Legacy: `transporte_validacion_salidas` (tabla pequeña, JSON `datos`)
leída por `get_valid_trans` (`base_salida_transporte.php` 613–650) en la
pestaña de informes; el JSON `datos` se revisita en F0 (decisión del
plan §4: mientras se decide su forma definitiva, se persiste tal cual).

Reglas:
- UNA fila por (área, mes, año) — `UniqueConstraint` del modelo.
- Quién puede cerrar: jefe validador del ÁREA (A1, `JefeValidador`) o
  programación/admin (§5.9). El cierre mensual es la puerta que luego
  usan las sábanas (§5.2) para decidir si un período editable sigue
  abierto.
"""
from django.db import IntegrityError, transaction

from apps.empleados.models import Empleado

from ..models import ValidacionSalida
from .periodos import entero, validar_anio, validar_mes, validar_periodo
from .salida_service import SalidaService


class ValidacionService:
    """Única capa de reglas de las validaciones mensuales por área."""

    # ------------------------------------------------------------------ #
    # Consulta (reemplaza `get_valid_trans`)
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar(query_params=None):
        """
        Filtros: mes, anio, area. Legacy filtraba por (mes, año) y el
        frontend desplegaba por área; aquí se agrega el filtro de área
        porque la tabla es por (área, mes, año).
        """
        query_params = query_params or {}
        queryset = ValidacionSalida.objects.all()

        mes = (query_params.get("mes") or "").strip()
        if mes:
            queryset = queryset.filter(mes=validar_mes(entero(mes, "mes")))

        anio = (query_params.get("anio") or "").strip()
        if anio:
            queryset = queryset.filter(
                anio=validar_anio(entero(anio, "anio"))
            )

        area = (query_params.get("area") or "").strip()
        if area:
            queryset = queryset.filter(area__iexact=area)

        return queryset.order_by("-anio", "-mes", "area")

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def cerrar_area(cls, datos, usuario=None):
        """
        Upsert del cierre mensual de un área (mes, anio, datos).

        Autorización: jefe validador del área (A1) o programación/admin
        (§5.9). `datos` es el JSON de contexto del cierre (forma
        libre hasta F0, como el legacy).
        """
        area = str(datos.get("area") or "").strip()
        if not area:
            raise ValueError("Debe indicar el área a validar.")
        mes, anio = validar_periodo(datos.get("mes"), datos.get("anio"))

        if not SalidaService._puede_programar(usuario) and not (
            SalidaService._es_jefe_de(usuario, area)
        ):
            raise ValueError(
                "No tiene permisos para validar las salidas de esta área."
            )

        payload = {
            "area": area,
            "mes": mes,
            "anio": anio,
            "datos": datos.get("datos") or {},
        }
        empleado = SalidaService._empleado_de(usuario)
        # Doble cierre previo defensivo (el UNIQUE es la garantía real);
        # evita dejar la transacción MySQL en estado roto con un
        # IntegrityError que luego se enmascara como ValueError.
        if ValidacionSalida.objects.filter(
            area=area, mes=mes, anio=anio
        ).exists():
            raise ValueError(
                "Ya existe un cierre registrado para ese área y período."
            )
        try:
            return ValidacionSalida.objects.create(
                **payload, creado_por=empleado
            )
        except IntegrityError:
            raise ValueError(
                "Ya existe un cierre registrado para ese área y período."
            )
