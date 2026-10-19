"""
Festivos colombianos — utilidad compartida entre módulos.

    from apps.common.festivos import es_festivo, es_dia_habil, sumar_dias_habiles

Reexporta la API pública de `calendario.py` (algoritmo de los 18 estatutarios
+ catálogo editable `festivos_colombia.json`). Para agregar un festivo basta
editar el JSON y llamar `recargar_catalogo()` (o reiniciar el proceso); no
requiere tocar Python ni correr migraciones.
"""
from .calendario import (
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
