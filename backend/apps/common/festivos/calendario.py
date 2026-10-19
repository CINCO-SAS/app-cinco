"""
Calendario festivo de Colombia — algoritmo + catálogo editable.

Módulo REUTILIZABLE (cualquier app puede importarlo):
    from apps.common.festivos import es_festivo, es_dia_habil

Dos fuentes, una sola API:

1) **Algoritmo** — port 1:1 de `frontend/src/utils/festivos/festivosColombia.ts`:
   los 18 festivos estatutarios (Ley 51 de 1983 "Ley Emiliani" + Pascua por el
   algoritmo de Butcher/Meeus) se CALCULAN, no se listan: válidos para cualquier
   año y sin mantenimiento de datos.

2) **Catálogo `festivos_colombia.json`** — fuente EDITABLE por año→mes, con la
   forma `{fecha, motivo}`. Es el equivalente moderno de "agregar un festivo a
   mano": añade el objeto al mes correspondiente, commitea y reinicia (o llama
   `recargar_catalogo()`), y la fecha ya no es hábil. Sirve para feriados
   decretados (art. 71 Ley 51) y para cualquier día que el negocio decida
   tratar como no laborable. Cubre 2022–2030; fuera de ese rango manda el
   algoritmo. El catálogo viene VALIDADO contra el algoritmo por la suite
   (`FestivosAlgoritmoYCatalogoTests`): si algún día contradice a un
   estatutario, las pruebas avisan. Corrección ya aplicada sobre la copia
   del repo: San Pedro y San Pablo 2027 estaba en el lunes ANTERIOR
   (2027-06-28) y la Ley Emiliani ordena el SIGUIENTE → 2027-07-05.

Reglas de combinación (decisión registrada):
- `es_festivo` = **algoritmo ∪ catálogo** (unir, no reemplazar): agregar en el
  JSON solo AGREGA festivos, nunca quita los estatutarios.
- `festivo_nombre` prioriza el nombre del algoritmo y solo consulta el catálogo
  si el algoritmo no lo conoce → los nombres dorados ya testeados
  ("Batalla de Boyacá", "Navidad") no cambian, y los extras del catálogo
  ("Día de la Virgen de Chiquinquirá") sí quedan rotulados.
- `calcular_festivos_colombia` sigue devolviendo exactamente los 18
  estatutarios (es el contrato testeado); para el listado completo con extras
  usar `festivos_del_anio`.

Diferencia de API con el original TS: trabaja con `datetime.date` (acepta
también `datetime` y strings ISO 'YYYY-MM-DD') en vez de strings, para
encajar con los DateField del backend.

Semántica de día hábil — decisión registrada:
- El frontend asume `sabado_habil=True` (operaciones/logística) y así
  se portó (mismo valor por defecto).
- El legacy CR-9 (`base_salida_transporte.php` 77–96) EXCLUÍA sábados:
  `if (!$esSab && !$esDom && !$esFest)`. Quien implemente la ventana
  CR-9 en `SalidaService` debe pasar `sabado_habil=False` explícito
  para conservar paridad con el comportamiento productivo.

TODO(G1): cuando exista `common.Festivo` (BD), la combinación pasa a ser
"algoritmo ∪ catálogo ∪ filas de BD" — el Gobierno decreta en caliente y eso
vive en la tabla; el JSON sigue siendo el editable rápido de escritorio.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

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

# ------------------------- catálogo editable (JSON) ------------------------- #

_RUTA_CATALOGO = Path(__file__).with_name("festivos_colombia.json")

# date → motivo, aplanado desde {año: {mes: [{fecha, motivo}]}}.
_CATALOGO = {}


def _leer_catalogo(ruta):
    """Carga el catálogo JSON → {date: motivo}. Archivo ausente/malformado = vacío."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}

    catalogo = {}
    for meses in datos.values():
        if not isinstance(meses, dict):
            continue
        for items in meses.values():
            if not isinstance(items, list):
                continue
            for item in items:
                try:
                    catalogo[date.fromisoformat(str(item["fecha"]).strip()[:10])] = item["motivo"]
                except (KeyError, TypeError, ValueError):
                    continue
    return catalogo


def recargar_catalogo(ruta=None):
    """Vuelve a leer el catálogo (por defecto el embebido) y devuelve el dict.

    Útil tras editar `festivos_colombia.json` sin reiniciar el proceso; las
    pruebas lo usan con una ruta temporal para simular "agregar un festivo".
    """
    global _CATALOGO
    _CATALOGO = _leer_catalogo(ruta or _RUTA_CATALOGO)
    return _CATALOGO


_CATALOGO = _leer_catalogo(_RUTA_CATALOGO)

# ------------------------------- algoritmo --------------------------------- #


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
    """Los 18 festivos estatutarios del año: lista [(date, nombre)] ordenada.

    No incluye extras del catálogo; ver `festivos_del_anio` para el listado
    completo (estatutarios ∪ catálogo).
    """
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


def festivos_del_anio(anio):
    """[(date, nombre)] ordenada = 18 estatutarios ∪ catálogo del año.

    El nombre del algoritmo gana sobre el del catálogo (nombres testeados).
    """
    completo = dict(calcular_festivos_colombia(anio))
    for fecha, motivo in _CATALOGO.items():
        if fecha.year == anio:
            completo.setdefault(fecha, motivo)
    return sorted(completo.items())


def festivo_nombre(valor):
    """Nombre del festivo si la fecha lo es; si no, None.

    Algoritmo primero (nombres dorados ya testeados); el catálogo solo aporta
    los festivos que el algoritmo no calcula (feriados decretados).
    """
    fecha = _a_fecha(valor)
    for festivo, nombre in calcular_festivos_colombia(fecha.year):
        if festivo == fecha:
            return nombre
    return _CATALOGO.get(fecha)


def es_festivo(valor):
    """¿La fecha es festivo colombiano? Unión: catálogo ∪ estatutarios."""
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
