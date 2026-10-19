"""
Shim: el calendario vive en `apps.common.festivos` (reutilizable por cualquier
módulo). Este módulo solo re-exporta para no romper los imports históricos de
transporte (`from .calendario import ...`, `from . import calendario`).

El comportamiento es el de `apps.common.festivos.calendario`: 18 estatutarios
por algoritmo ∪ catálogo editable `festivos_colombia.json`. Ver el docstring
de allí para las decisiones registradas (CR-9 / `sabado_habil=False`, y el
nombre del algoritmo por sobre el del catálogo).
"""
from apps.common.festivos.calendario import (  # noqa: F401
    calcular_festivos_colombia,
    es_dia_habil,
    es_festivo,
    festivo_nombre,
    festivos_del_anio,
    recargar_catalogo,
    restar_dias_habiles,
    sumar_dias_habiles,
)

__all__ = [
    "calcular_festivos_colombia",
    "es_dia_habil",
    "es_festivo",
    "festivo_nombre",
    "festivos_del_anio",
    "recargar_catalogo",
    "restar_dias_habiles",
    "sumar_dias_habiles",
]
