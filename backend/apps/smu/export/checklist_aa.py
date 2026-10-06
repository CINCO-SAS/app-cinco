"""Textos de los 39 parámetros del checklist del preventivo de AA.

Espejo de ``CHECKLIST_ITEMS_AA`` (frontend) y de la columna
``SmuDetallePreventivoAaChecklist.item_numero``: el modelo solo guarda el
número y el estado, así que el Excel necesita este catálogo para escribir
el párrafo de cada fila de la sección "LISTA DE CHEQUEO GENERAL".
"""
from __future__ import annotations

PARAMETROS_CHECKLIST_AA: dict[int, str] = {
    1: "La fijación de las unidades condensadoras es la adecuada",
    2: "La fijación de las unidades manejadoras es la adecuada",
    3: "El anclaje y fijación de tuberías es el adecuado",
    4: (
        "Las unidades condensadoras y manejadoras se encuentran en buenas "
        "condiciones físicas."
    ),
    5: "Los manuales se encuentran con las unidades",
    6: "Se encuentra el control remoto de las unidades (Cuando Aplique)",
    7: "Serpentín de unidades condensadoras están limpios y en buenas condiciones",
    8: "Buena circulación de aire natural en las unidades condensadoras",
    9: "Existen Fugas de aire acondicionado en el cuarto",
    10: (
        "Las tuberías de conexión entre las unidades condensadoras y "
        "manejadoras no presentan signos de maltrato, golpes, fugas de "
        "refrigerante, o signos de óxido o corrosión"
    ),
    11: "Rejilla de control de dirección de aire frío funcional y en buen estado",
    12: (
        "Chasis de las unidades condensadora o manejadora está libre de óxido o "
        "corrosión"
    ),
    13: "El tubo de drenaje del agua condensadora se encuentra libre de obstrucciones.",
    14: "Las conexiones eléctricas se encuentran en buenas condiciones",
    15: (
        "Unidad Condensadoras funcionan adecuadamente (sin ruidos o vibraciones "
        "extrañas)"
    ),
    16: "Unidad Manejadora funcionan adecuadamente (sin ruidos o vibraciones extrañas)",
    17: (
        "Los Elementos Electrónicos de Control (Pulsadores, Selectores, "
        "Contactores, Relés) funcionan adecuadamente."
    ),
    18: "El estado de Lubricación y Rodamientos de las unidades es el adecuado.",
    19: "El estado de los ejes y chumaceras es el adecuado.",
    20: "La Tarjeta de Control de Aire Acondicionado opera adecuadamente.",
    21: (
        "Se presentan alarmas en las unidades del aire acondicionado (Sonora, "
        "Visual, etc.)"
    ),
    22: "Se presentan fugas de Refrigerante en serpentines y tuberías.",
    23: "La válvula Solenoide opera adecuadamente.",
    24: "Los Filtros de Secado se encuentran operando adecuadamente.",
    25: "El Aislamiento térmico se encuentra en buenas condiciones.",
    26: "Nivel de enfriamiento Adecuado (Menor a 4°C En Rejillas de Salida)",
    27: "Reinicio automático (con corte de energía se reinicia la operación)",
    28: "Se garantiza la distribución de aire frío por todo el cuarto",
    29: (
        "El display se encuentra en perfectas condiciones y no presenta alarmas "
        "activas o códigos de error en el display"
    ),
    30: (
        "El Chasis del aire acondicionado está debidamente puesto a tierra "
        "(Unidad Condensadora y Unidad Manejadora)"
    ),
    31: (
        "Sistema de potencia y control de los aires acondicionados está puesto "
        "a tierra de forma adecuada"
    ),
    32: "Ductería del aire acondicionado en buen estado.",
    33: (
        "Dimensionamiento de las protecciones Eléctricas de Equipos "
        "(Manejadora-Condensadora) es el adecuado y se encuentran en buen "
        "estado."
    ),
    34: "Correas Manejadoras en buen estado.",
    35: "Gestión Remota (RTU) funciona adecuadamente.",
    36: "Aspa del Ventilador se encuentra en buen estado y funciona adecuadamente.",
    37: "Se requiere reforzar la seguridad del Equipo (Implementar Rejillas).",
    38: "Drenaje funciona adecuadamente y se encuentra en buen estado.",
    39: "Equipo requiere cambio por obsolescencia",
}


def parametro_de(numero: int) -> str:
    """Texto del parámetro `numero`; si no existe, un rótulo genérico."""
    return PARAMETROS_CHECKLIST_AA.get(numero, f'PARÁMETRO {numero}')
