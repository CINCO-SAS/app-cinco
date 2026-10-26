"""
Acceso a la BD negra (Nokia) — líneas corporativas de un móvil.

Fuente: legacy `base_transportadores.php` 75 (acción `get_telefonos_conductores`):

    SELECT group_concat(distinct numero) as numeros
    FROM cincosas_cincosas.nokia_base_lineas
    WHERE asignado = ? LIMIT 1

Lo que el legacy guardaba en `cinco_base_de_personal.placa` y en
`nokia_base_infraestructura.placa` (BD negra) son las DOS fuentes de verdad
de la placa de un móvil; de ahí que D-A9 siga abierta: falta decidir cuál
manda.

GATE G4 / D-A10: el alias `negra` SÍ está en `DATABASES` desde el commit
`e90dd84` (con las variables `DB_NEGRA_*`). La función sigue DEGRADANDO
mientras la BD negra no responda (devuelve lista vacía y
`disponible=False`, sin un 500): el cierre operativo del gate es
apuntar las variables al servidor real en producción y verificar la
conectividad (C4).
"""
from django.conf import settings

# Alias de la base negra en DATABASES.
ALIAS_NOKIA = "negra"

# Tabla y columnas (del SQL del legacy).
TABLA_NOKIA_LINEAS = "nokia_base_lineas"
COLUMNA_NOKIA_NUMERO = "numero"
COLUMNA_NOKIA_ASIGNADO = "asignado"


def nokia_configurada():
    """¿Está configurado el alias de la BD negra en `DATABASES`?"""
    return ALIAS_NOKIA in settings.DATABASES


def lineas_nokia(cedula):
    """
    Números de línea corporativa asignados a `cedula` en la BD negra.

    Devuelve `(lineas, disponible)`:
      · `lineas`    — lista de números (vacía si no hay o no se pudo consultar).
      · `disponible` — True si la BD negra respondió; False si no está
        configurada (gate G4) o si falló.

    Degrada sin lanzar: la información de contacto es un extra, no un flujo
    crítico. Si la BD no responde, se entrega el resto de la ficha igual.
    """
    if not cedula:
        return [], False
    if not nokia_configurada():
        return [], False

    from django.db import connections

    try:
        with connections[ALIAS_NOKIA].cursor() as cursor:
            cursor.execute(
                f"SELECT DISTINCT `{COLUMNA_NOKIA_NUMERO}` "  # noqa: S608
                f"FROM `{TABLA_NOKIA_LINEAS}` "
                f"WHERE `{COLUMNA_NOKIA_ASIGNADO}` = %s",
                [cedula],
            )
            filas = cursor.fetchall()
    except Exception:  # noqa: BLE001 - la BD negra es opcional (gate G4)
        return [], False

    numeros = []
    for (numero,) in filas:
        if numero is None:
            continue
        texto = str(numero).strip()
        if texto and texto not in numeros:
            numeros.append(texto)
    return numeros, True
