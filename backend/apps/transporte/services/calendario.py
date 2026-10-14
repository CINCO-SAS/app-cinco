"""
Calendario festivo de Colombia — port del frontend al backend.

Port 1:1 de `frontend/src/utils/festivos/festivosColombia.ts`: los 18
festivos estatutarios (Ley 51 de 1983 "Ley Emiliani" + Pascua por el
algoritmo de Butcher/Meeus) se CALCULAN, no se listan: válidos para
cualquier año y sin mantenimiento de datos.

Diferencia de API con el original: trabaja con `datetime.date` (acepta
también `datetime` y strings ISO 'YYYY-MM-DD') en vez de strings, para
encajar con los DateField del backend.

Semántica de día hábil — decisión registrada:
- El frontend asume `sabado_habil=True` (operaciones/logística) y así
  se portó (mismo valor por defecto).
- El legacy CR-9 (`base_salida_transporte.php` 77–96) EXCLUÍA sábados:
  `if (!$esSab && !$esDom && !$esFest)`. Quien implemente la ventana
  CR-9 en `SalidaService` debe pasar `sabado_habil=False` explícito
  para conservar paridad con el comportamiento productivo.

TODO(G1): cuando exista `common.Festivo` (otra área), `es_festivo`
pasa a ser "algoritmo ∪ filas de BD" — el Gobierno puede decretar
festivos adicionales (art. 71 Ley 51) y eso sí vive en la tabla.
"""
from datetime import date, datetime, timedelta

# Caché por año (el original cachéa igual): O(1) en llamadas repetidas.
_CACHE_POR_ANIO = {}

# Festivos inamovibles: (mes, día, nombre).
_FIJOS = (
    (1, 1, "Año Nuevo"),
    (5, 1, "Día del Trabajo"),
    (7, 20, "Día de la Independencia"),
    (8, 7, "Batalla de Boyacá"),
    (12, 8, "Inmaculada Concepción"),
    (12, 25, "Navidad"),
)

# Con Ley Emiliani (traslado al lunes siguiente): (mes, día, nombre).
# OJO: en el original TS el mes era 0-based; aquí 1-based (datetime.date).
_EMILIANI = (
    (1, 6, "Día de los Reyes Magos"),
    (3, 19, "Día de San José"),
    (6, 29, "San Pedro y San Pablo"),
    (8, 15, "Asunción de la Virgen"),
    (10, 12, "Día de la Raza"),
    (11, 1, "Todos los Santos"),
    (11, 11, "Independencia de Cartagena"),
)

# Desplazamientos desde el Domingo de Pascua (ya con Emiliani aplicado):
# (delta de días, nombre).
_RELATIVOS_PASCUA = (
    (-3, "Jueves Santo"),
    (-2, "Viernes Santo"),
    (43, "Ascensión del Señor"),
    (64, "Corpus Christi"),
    (71, "Sagrado Corazón de Jesús"),
)


def _a_fecha(valor):
    """date | datetime | 'YYYY-MM-DD' → date (para aceptar todo tipo de entrada)."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor).strip()[:10])


def _calcular_pascua(anio):
    """Domingo de Resurrección — algoritmo de Butcher / Meeus (Gregoriano)."""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31          # 3 = marzo, 4 = abril
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def _aplicar_ley_emiliani(fecha):
    """Si no cae en lunes, se traslada al lunes siguiente."""
    if fecha.weekday() == 0:  # lunes
        return fecha
    dias_para_lunes = 7 - fecha.weekday()
    return fecha + timedelta(days=dias_para_lunes)


def calcular_festivos_colombia(anio):
    """Los 18 festivos estatutarios del año: lista [(date, nombre)] ordenada."""
    if anio in _CACHE_POR_ANIO:
        return _CACHE_POR_ANIO[anio]

    pascua = _calcular_pascua(anio)
    festivos = [(_aplicar_ley_emiliani(date(anio, mes, dia)), nombre)
                for mes, dia, nombre in _EMILIANI]
    festivos.extend((date(anio, mes, dia), nombre) for mes, dia, nombre in _FIJOS)
    festivos.extend((pascua + timedelta(days=delta), nombre)
                    for delta, nombre in _RELATIVOS_PASCUA)
    festivos.sort()

    _CACHE_POR_ANIO[anio] = festivos
    return festivos


def festivo_nombre(valor):
    """Nombre del festivo si la fecha lo es; si no, None."""
    fecha = _a_fecha(valor)
    for festivo, nombre in calcular_festivos_colombia(fecha.year):
        if festivo == fecha:
            return nombre
    return None


def es_festivo(valor):
    """¿La fecha es festivo estatutario colombiano?"""
    return festivo_nombre(valor) is not None


def es_dia_habil(valor, sabado_habil=True):
    """Domingo nunca; festivo nunca; sábado según `sabado_habil` (default
    True, igual que el frontend — la CR-9 legacy pasa False, ver módulo)."""
    fecha = _a_fecha(valor)
    if fecha.weekday() == 6:  # domingo
        return False
    if fecha.weekday() == 5 and not sabado_habil:  # sábado
        return False
    return not es_festivo(fecha)


def sumar_dias_habiles(valor, n, sabado_habil=True):
    """Suma N días hábiles (n negativo = restar); devuelve date."""
    fecha = _a_fecha(valor)
    if n == 0:
        return fecha
    paso = 1 if n > 0 else -1
    agregados = 0
    while agregados < abs(n):
        fecha += timedelta(days=paso)
        if es_dia_habil(fecha, sabado_habil=sabado_habil):
            agregados += 1
    return fecha


def restar_dias_habiles(valor, n, sabado_habil=True):
    """Resta N días hábiles; devuelve date (alias de sumar con n negativo)."""
    return sumar_dias_habiles(valor, -n, sabado_habil=sabado_habil)
