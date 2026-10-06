"""Generación de archivos Excel de exporte por formulario SMU.

El dispatch es por la pareja ``(categoria, tipo_formulario)`` de la actividad:
cada combinación tiene su plantilla de estilo. Las que todavía no existen
lanzan :class:`ExporteNoSoportado` y la vista responde con un 400 explicativo.
"""
from __future__ import annotations

import re
import unicodedata
from io import BytesIO

from apps.smu.models import SmuActividad

CONTENT_TYPE_XLSX = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


class ExporteNoSoportado(Exception):
    """El tipo de formulario de la actividad aún no tiene plantilla de exporte."""


def _generador_de(actividad: SmuActividad):
    clave = (actividad.categoria, actividad.tipo_formulario)

    # Import perezoso: evita un import circular con los generadores,
    # que a su vez importan los modelos de esta app.
    from .capex import generar_excel_capex
    from .emergencia import generar_excel_emergencia
    from .preventivo_aa import generar_excel_preventivo_aa
    from .planta import generar_excel_preventivo_planta

    registro = {
        ("emergencias", "estandar"): generar_excel_emergencia,
        ("correctivos", "estandar"): generar_excel_emergencia,
        ("preventivos", "aire_acondicionado"): generar_excel_preventivo_aa,
        ("preventivos", "planta"): generar_excel_preventivo_planta,
        ("correctivos_capex", "tipologia1"): generar_excel_capex,
        ("correctivos_capex", "tipologia3"): generar_excel_capex,
        ("correctivos_capex", "tipologia5"): generar_excel_capex,
    }
    return registro.get(clave)


def nombre_archivo(actividad: SmuActividad) -> str:
    """`emergencia_ESTACION_1234.xlsx` — slug simple, sin tildes ni espacios raros."""
    prefijos = {
        ("emergencias", "estandar"): "emergencia",
        ("correctivos", "estandar"): "correctivo",
        ("preventivos", "aire_acondicionado"): "preventivo_aa",
        ("preventivos", "planta"): "preventivo_planta",
        ("correctivos_capex", "tipologia1"): "capex_tipologia1",
        ("correctivos_capex", "tipologia3"): "capex_tipologia3",
        ("correctivos_capex", "tipologia5"): "capex_tipologia5",
    }
    prefijo = prefijos.get(
        (actividad.categoria, actividad.tipo_formulario), "formulario"
    )
    estacion = unicodedata.normalize("NFD", actividad.nombre_estacion or "")
    estacion = "".join(c for c in estacion if unicodedata.category(c) != "Mn")
    estacion = re.sub(r"[^A-Za-z0-9]+", "_", estacion).strip("_")[:40] or "SIN_ESTACION"
    referencia = (actividad.codigo_ot or "").strip()
    referencia = re.sub(r"[^A-Za-z0-9]+", "", referencia)[:30] or str(actividad.id)
    return f"{prefijo}_{estacion}_{referencia}.xlsx"


def _etiqueta(choices, valor: str) -> str:
    """Etiqueta legible de un choice; si no está, devuelve el valor crudo."""
    return dict(choices).get(valor, valor)


def generar_excel_actividad(actividad: SmuActividad) -> tuple[bytes, str]:
    """Devuelve ``(contenido_xlsx, nombre_de_archivo)`` de la actividad."""
    generador = _generador_de(actividad)

    if generador is None:
        # `tipo_formulario` no declara choices en el modelo (ver `TIPO_FORMULARIO_CHOICES`),
        # así que no existe get_tipo_formulario_display(): se resuelve a mano.
        tipo = _etiqueta(
            SmuActividad.TIPO_FORMULARIO_CHOICES, actividad.tipo_formulario
        )
        raise ExporteNoSoportado(
            f"El formulario «{actividad.get_categoria_display()} / {tipo}» aún "
            f"no tiene plantilla de exporte."
        )

    libro = generador(actividad)
    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue(), nombre_archivo(actividad)


__all__ = [
    "CONTENT_TYPE_XLSX",
    "ExporteNoSoportado",
    "generar_excel_actividad",
    "nombre_archivo",
]
