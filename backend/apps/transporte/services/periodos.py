"""
Matemática y validación de períodos (mes/año) del módulo transporte.

Fuente única de verdad compartida por ParametrosService (cierres, §5.8) y
LiquidacionService (liquidaciones, §5.2): límites de período, rango de fechas
de un mes y retroceso mensual (CR-10: retrospectiva de 6 meses).

El retroceso replica la aritmética de `strtotime('-N month')` del legacy
(base_salida_transporte.php 333) sobre el primer día del mes.
"""
from datetime import date

# Períodos plausibles de operación (legacy opera desde 2021; margen holgado).
MES_MIN, MES_MAX = 1, 12
ANIO_MIN, ANIO_MAX = 2015, 2100


def entero(valor, nombre):
    """Convierte a int con mensaje estable (contrato de los services)."""
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El campo {nombre} debe ser un número entero.")


def validar_mes(mes):
    if not MES_MIN <= mes <= MES_MAX:
        raise ValueError(f"El mes debe estar entre {MES_MIN} y {MES_MAX}.")
    return mes


def validar_anio(anio):
    if not ANIO_MIN <= anio <= ANIO_MAX:
        raise ValueError(f"El año debe estar entre {ANIO_MIN} y {ANIO_MAX}.")
    return anio


def validar_periodo(mes, anio):
    """Valores crudos → (mes, anio) enteros validados, en ese orden."""
    return validar_mes(entero(mes, "mes")), validar_anio(entero(anio, "anio"))


def rango_mes(mes, anio):
    """[primer día del mes, primer día del mes siguiente): exclusión superior
    al estilo YEAR()/MONTH() del legacy sin atarse a un dialecto SQL."""
    desde = date(anio, mes, 1)
    hasta = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
    return desde, hasta


def restar_meses(mes, anio, n):
    """(mes, anio) menos n meses (aritmética proleptica, sin saltos de era)."""
    total = anio * 12 + (mes - 1) - n
    return (total % 12) + 1, total // 12


def es_periodo_actual(mes, anio):
    """¿El período pedido es el mes en curso? (gate del retroceso CR-10.)"""
    hoy = date.today()
    return (mes, anio) == (hoy.month, hoy.year)
