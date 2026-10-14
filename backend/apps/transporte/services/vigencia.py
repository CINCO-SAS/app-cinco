"""
Regla de semáforo de vigencia — compartida por todo el módulo.

La misma regla verificada en el código legacy gobierna:
- SOAT/CDA del vehículo  (base_salida_transporte.php 2022–2024, §5.3)
- Licencia del conductor  (§5.4)

Umbrales: >60 días VIGENTE · 31–60 POR_VENCER · ≤30 o vencida VENCIDA.
"""
from datetime import date

DIAS_VERDE = 60
DIAS_NARANJA = 30

VIGENTE = "VIGENTE"
POR_VENCER = "POR_VENCER"
VENCIDA = "VENCIDA"
SIN_REGISTRO = "SIN_REGISTRO"


def estado_vigencia(fecha_vencimiento, hoy=None):
    """
    Estado documental calculado EN SERVIDOR a partir de una fecha de
    vencimiento. Nunca se persiste: se deriva en cada consulta.
    """
    if not fecha_vencimiento:
        return SIN_REGISTRO
    hoy = hoy or date.today()
    dias = (fecha_vencimiento - hoy).days
    if dias > DIAS_VERDE:
        return VIGENTE
    if dias > DIAS_NARANJA:
        return POR_VENCER
    return VENCIDA
