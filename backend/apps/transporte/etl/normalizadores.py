"""
Normalizadores de la ETL legacy → Django (§7.2/§7.3).

El legacy mezcla caja y formatos: estados 'reportado' vs 'APROBADO' (D-A6),
booleanos 'SI'/'NO', fechas '0000-00-00' y datetimes ingenuos en hora Bogotá
con el hack PHP '-5 hour' (D-A4). Aquí se normaliza UNA vez; cualquier fila
que no se pueda convertir lanza ValueError con el motivo exacto, que el
comando acumula en el reporte de "filas no convertibles" (§7.2).
"""
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.utils import timezone

from ..models.choices import EstadoSalida

# Zona real del legacy (D-A4: fin del hack -5 hour).
TZ_LEGACY = ZoneInfo("America/Bogota")

FECHA_CERO = "0000-00-00"
SI = ("SI", "SÍ", "1", "TRUE", "S")
NO = ("NO", "0", "FALSE")


def texto(valor, campo="campo", requerido=False):
    """str recortado; vacío → error si es requerido."""
    limpio = "" if valor is None else str(valor).strip()
    if requerido and not limpio:
        raise ValueError(f"{campo} vacío")
    return limpio


def entero(valor, campo, opcional=False, por_defecto=None):
    """int desde texto ('2020', kilometraje varchar…); opcional → None."""
    if valor is None or str(valor).strip() == "":
        if opcional:
            return por_defecto
        raise ValueError(f"{campo} vacío")
    try:
        return int(str(valor).strip())
    except ValueError:
        raise ValueError(f"{campo} '{valor}' no es numérico")


def decimal(valor, campo, por_defecto="0"):
    """Decimal para valores monetarios; vacío → por_defecto."""
    if valor is None or str(valor).strip() == "":
        valor = por_defecto
    try:
        return Decimal(str(valor).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{campo} '{valor}' no es numérico")


def normalizar_estado(valor):
    """D-A6: mayúsculas y catálogo; fuera de él → error de fila."""
    limpio = texto(valor, "estado", requerido=True).upper()
    if limpio not in EstadoSalida.values:
        raise ValueError(f"estado '{valor}' fuera de catálogo")
    return limpio


def normalizar_catalogo(valor, permitidos, campo):
    """Mayúsculas + espacios→_ para choices (tipo_vehiculo, tipo_contrato…)."""
    limpio = texto(valor, campo, requerido=True).upper().replace(" ", "_")
    if limpio not in permitidos:
        raise ValueError(f"{campo} '{valor}' no es un valor válido")
    return limpio


def booleano_si_no(valor):
    """'SI'/'NO' (y 1/0/true/false) → bool; vacío → False."""
    if isinstance(valor, bool):
        return valor
    limpio = str(valor or "").strip().upper()
    if limpio in SI:
        return True
    if limpio in NO or limpio == "":
        return False
    raise ValueError(f"'{valor}' no es un booleano SI/NO")


def activo_por_estado(valor, activo_por_defecto=True):
    """legacy estado texto → bool (INACTIVO/NO/0 → False)."""
    limpio = str(valor or "").strip().upper()
    if limpio in ("INACTIVO", "NO", "0", "BAJA"):
        return False
    if limpio in ("ACTIVO", "SI", "1", ""):
        return activo_por_defecto
    raise ValueError(f"estado '{valor}' no es reconocido (ACTIVO/INACTIVO)")


def fecha_legacy(valor, campo="fecha"):
    """'0000-00-00'/vacío → None; si no, date ISO."""
    if valor is None:
        return None
    limpio = str(valor).strip()
    if limpio == "" or limpio.startswith(FECHA_CERO):
        return None
    try:
        return date.fromisoformat(limpio[:10])
    except ValueError:
        raise ValueError(f"{campo} '{valor}' no es una fecha")


def datetime_legacy(valor, campo="fecha"):
    """Datetime ingenuo del legacy → aware en America/Bogota (D-A4).

    El PHP restaba '-5 hour' a mano; aquí la zona se declara y Django
    almacena en UTC con USE_TZ=True.
    """
    if valor is None or str(valor).strip() == "":
        raise ValueError(f"{campo} vacía")
    limpio = str(valor).strip().replace("T", " ")
    if limpio.startswith(FECHA_CERO):
        raise ValueError(f"{campo} '{valor}' es fecha cero")
    try:
        ingenuo = datetime.fromisoformat(limpio)
    except ValueError:
        raise ValueError(f"{campo} '{valor}' no es un datetime")
    if ingenuo.tzinfo is not None:
        return ingenuo
    return timezone.make_aware(ingenuo, TZ_LEGACY)


def json_columna(valor):
    """Columna datos/historial (texto JSON) → dict/list; inválido → None
    (el convertidor decide si es error o advertencia)."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (dict, list)):
        return valor
    try:
        return json.loads(valor)
    except (ValueError, TypeError):
        return None
