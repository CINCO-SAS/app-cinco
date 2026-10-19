"""
InformeService — Tab 2 Informes / sábana (§5.7).

F5-1 `cuenta_cobro`: cuenta de cobro imprimible del alquiler de un
vehículo por mes. Legacy `cuenta_cobro_plantilla.php`, que la sábana
invocaba desde la tabla de liquidación con un `data_cc` JSON.

**Mejora de integridad sobre el legacy** (decisión del módulo: usarlo de
guía pero refactorizarlo cuando es inseguro): el legacy recibía en campos
ocultos del formulario `pagar`, `banco`, `cuenta_pago`, `nombre_pago`,
`cedula_pago` y los imprimía tal cual — cualquier usuario podía alterar el
importe desde el navegador antes de imprimir. Aquí el importe se calcula
en el SERVIDOR desde las salidas del mes (`total_a_pagar` = valor_dia ±
novedad) y el pagador se lee de `DatosBancariosVehiculo` en BD; la
entrada es solo placa + periodo.

Fórmula (idéntica a la liquidación de la sábana, JS 4270–4336):
- valor_base = Σ salida.total_a_pagar (valor_dia ± novedad)
- retefuente = 1 % de valor_base; pagar = valor_base − retefuente
"""
import calendar
import csv
import io
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html import escape

from openpyxl import Workbook

from ..models import (
    ConsecutivoMensual,
    DatosBancariosVehiculo,
    Salida,
    Vehiculo,
)
from ..models.choices import EstadoSalida, TipoContrato
from .periodos import rango_mes, validar_periodo

# Retefuente del legacy (sábana: `valor_base * 0.01`).
RETEFUENTE = Decimal("0.01")

CERO = Decimal("0.00")

MESES = (
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
)

# Encabezado legal de la cuenta de cobro (plantilla legacy).
EMPRESA = "COMPAÑÍA INTEGRAL NEGOCIOS DE COLOMBIA S.A.S"
NIT = "811042087-2"

# Cabecera del export (F5-4), en el orden de la tabla de la sábana.
COLUMNAS_EXPORT = (
    "FECHA", "PLACA", "CEDULA CONDUCTOR", "NOMBRE CONDUCTOR", "AREA",
    "CARPETA", "SEDE", "VALOR DIA", "NOVEDAD", "VALOR NOVEDAD",
    "TOTAL A PAGAR", "ESTADO", "OBSERVACION",
)


def _a_numero(valor):
    """
    Convierte una cadena numérica a `Decimal` para que las celdas XLSX
    queden como número real; si no es número, la deja tal cual.
    """
    if not isinstance(valor, str):
        return valor
    try:
        return Decimal(valor)
    except InvalidOperation:
        return valor


class InformeService:
    """Única capa de reglas de informes (Tab 2) del módulo transporte."""

    # `series_chart` (F5-2): como el legacy para todo dato posterior al
    # 01-08-2024 — solo VALIDADO y APROBADO cuentan en el gráfico.
    ESTADOS_GRAFICO = (EstadoSalida.VALIDADO, EstadoSalida.APROBADO)

    # Área que la sábana dibuja en el eje y secundario (derecha).
    AREA_EJE_SECUNDARIO = "I&M"

    # ------------------------------------------------------------------ #
    # Cuenta de cobro (F5-1)
    # ------------------------------------------------------------------ #
    @staticmethod
    def cuenta_cobro(placa, mes, anio):
        """
        Datos de la cuenta de cobro del vehículo `placa` para el periodo
        `mes`/`anio` — sin escribir BD.

        Devuelve el dict con el importe calculado en servidor, el pagador
        y los rótulos del periodo, listo para `html_cuenta_cobro`.
        """
        mes, anio = validar_periodo(mes, anio)
        placa = str(placa or "").strip().upper()
        vehiculo = Vehiculo.objects.filter(placa=placa).first()
        if vehiculo is None:
            raise ValueError(f"Vehículo no encontrado con placa {placa}.")

        desde, hasta = rango_mes(mes, anio)
        salidas = (
            Salida.objects.filter(
                vehiculo=vehiculo, fecha_salida__gte=desde, fecha_salida__lt=hasta
            )
            .exclude(estado=EstadoSalida.ELIMINADO)
            .select_related("novedad")
        )
        total_dias = salidas.count()
        valor_base = sum((salida.total_a_pagar for salida in salidas), CERO)
        retefuente = (valor_base * RETEFUENTE).quantize(Decimal("0.01"))
        pagar = valor_base - retefuente

        # Consecutivo del periodo si ya fue generado (A2); si no, vacío.
        consecutivo = (
            ConsecutivoMensual.objects.filter(
                vehiculo=vehiculo, mes=mes, anio=anio
            )
            .values_list("consecutivo", flat=True)
            .first()
        )

        datos = {
            "placa": placa,
            "mes": mes,
            "anio": anio,
            "nombre_mes": MESES[mes - 1],
            "ultimo_dia": calendar.monthrange(anio, mes)[1],
            "consecutivo": consecutivo or "",
            "total_dias": total_dias,
            "valor_base": valor_base,
            "retefuente": retefuente,
            "pagar": pagar,
        }
        datos.update(InformeService._pagador(vehiculo))
        return datos

    @staticmethod
    def _pagador(vehiculo):
        """
        Pagador: el dato bancario vigente del vehículo (CR-13); sin dato
        bancario, el propietario del vehículo (fallback del legacy).
        """
        bancario = (
            DatosBancariosVehiculo.objects.filter(vehiculo=vehiculo, activo=True)
            .order_by("-id")
            .first()
        )
        if bancario is not None:
            return {
                "cedula_pago": bancario.cedula_titular,
                "nombre_pago": bancario.nombre_titular,
                "tipo_cuenta": bancario.tipo_cuenta,
                "banco": bancario.banco,
                "cuenta_pago": bancario.numero_cuenta,
            }
        return {
            "cedula_pago": vehiculo.cedula_propietario or "",
            "nombre_pago": vehiculo.nombre_propietario or "",
            "tipo_cuenta": "",
            "banco": "",
            "cuenta_pago": "",
        }

    @staticmethod
    def html_cuenta_cobro(datos):
        """
        HTML imprimible fiel a `cuenta_cobro_plantilla.php` (el navegador
        lo abre en pestaña nueva e imprime a PDF). Todos los valores van
        escapados con `html.escape` — el legacy imprimía entrada del
        cliente en atributos y texto sin escapar.
        """

        def esc(valor):
            return escape(str(valor if valor is not None else ""))

        def dinero(valor):
            # "$ 1.234.567" (sábana formateaba enteros).
            return f"{int(valor):,}".replace(",", ".")

        mes_nombre = esc(datos["nombre_mes"])
        anio = datos["anio"]
        ultimo = datos["ultimo_dia"]
        return f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="es" lang="es">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>cuenta_de_cobro</title>
<style>
* {{ margin: 0; padding: 0; text-indent: 0; }}
body {{ font-family: "Century Gothic", sans-serif; color: black; text-align: -webkit-center; }}
.caja {{ background: #D9D9D9; border: 2pt solid #A6A6A6; display: block; text-align: center; }}
.caja-mes {{ min-height: 21pt; width: 105.8pt; }}
.caja-consecutivo {{ min-height: 21pt; width: 67.8pt; margin-right: 40px; float: inline-end; }}
.caja-concepto {{ min-height: 64.5pt; width: 498.8pt; text-align: left; }}
.caja-cuenta {{ min-height: 57pt; width: 499.4pt; text-align: left; }}
.caja-novedades {{ min-height: 69pt; width: 498.8pt; text-align: left; }}
.subrayado {{ text-decoration: underline; }}
.centro {{ text-align: center; }}
.nota {{ font-size: 9pt; }}
.linea-firma {{ display: inline-block; border-bottom: 1pt solid black; width: 45%; }}
</style>
</head>
<body>
<br />
<div class="caja caja-consecutivo"><strong>{esc(datos["consecutivo"])}</strong></div>
<div class="caja caja-mes">MES: {mes_nombre}</div>
<p style="padding-top: 11pt;"><br /></p>
<p>{EMPRESA}<br />NIT {NIT}</p>
<p style="padding-top: 8pt;"><br /></p>
<p class="centro">Debe a:</p>
<br />
<p class="centro"><span class="subrayado">{esc(datos["nombre_pago"])}</span></p>
<p style="padding-top: 12pt;"><br /></p>
<p class="centro">CEDULA: <span class="subrayado">{esc(datos["cedula_pago"])}</span></p>
<p style="padding-top: 12pt;"><br /></p>
<p class="centro">La suma de:</p>
<p class="centro">$ <span class="subrayado">{dinero(datos["pagar"])}</span></p>
<p style="padding-top: 12pt;"><br /></p>
<p class="centro">Por concepto de:</p>
<div class="caja caja-concepto" style="padding: 4pt 12pt;">
  <p><i>Alquiler del vehículo:</i></p>
  <p>Placa: <span class="subrayado">{esc(datos["placa"])}</span></p>
  <p>Días laborados <span class="subrayado">{esc(datos["total_dias"])}</span></p>
  <p>Del 01 de {mes_nombre} al {ultimo} de {mes_nombre} de {anio}</p>
</div>
<p style="padding-top: 12pt;"><br /></p>
<div class="caja caja-cuenta" style="padding: 1pt 11pt;">
  <p><i><b>Por favor consignar a la Cuenta de:</b></i><br /><br />
     Ahorro Banco <span class="subrayado">{esc(datos["banco"])}</span><br />
     Número <span class="subrayado">{esc(datos["cuenta_pago"])}</span></p>
</div>
<p style="padding-top: 12pt;"><br /></p>
<div class="caja caja-novedades" style="padding: 4pt 9pt;">
  <p><b>Novedades:</b></p>
</div>
<p style="padding-top: 9pt;"></p>
<p class="nota"><b>Nota</b>: Por políticas internas de la compañía, la cuenta
   de cobro deberá ser rellenada únicamente después de validar las planillas
   y confirmar la veracidad de la información.</p>
<p style="padding-top: 6pt;"></p>
<p>Para constancia se firma a los <u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u>
   días del mes de <u>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</u>
   del {anio}</p>
<p style="padding-top: 40pt;"></p>
<p><span class="linea-firma">&nbsp;</span><br />Firma quien elaboro:</p>
<p style="padding-top: 12pt;"><span class="linea-firma">&nbsp;</span><br />Firma autorización:</p>
</body>
</html>"""

    # ------------------------------------------------------------------ #
    # Serie del gráfico "Pagos por Mes, por Área" (F5-2)
    # ------------------------------------------------------------------ #
    @staticmethod
    def series_chart(anio=None):
        """
        F5-2: series del gráfico "Pagos por Mes, por Área" de la sábana
        (legacy `series_chart`, controlador 37–125).

        Devuelve ``{"series": [...]}``: una serie por área, con puntos
        ``["<mes>/1/<anio>", valor]`` (formato de tiempo que lee el eje X
        de la sábana) ordenados cronológicamente. El valor es la suma de
        ``total_a_pagar`` (valor_dia ± novedad) por (área, mes). El área
        **I&M** va al eje secundario con su estilo de línea/marcador.

        **Corrección sobre el legacy:** el PHP recibía ``mes``/``yyyy`` y
        luego ejecutaba ``execute([2024])``: fijaba 2024 a mano, ignoraba
        ambos parámetros y la sábana ni siquiera los enviaba. Aquí el año
        es un filtro opcional **respetado**; sin año, todo el histórico.

        **Estados:** como el legacy para todo dato posterior al 01-08-2024
        (la rama anterior, que sumaba también REPORTADO/RECHAZADO, es
        histórica): VALIDADO + APROBADO.
        """
        salidas = Salida.objects.filter(
            estado__in=InformeService.ESTADOS_GRAFICO
        ).filter(area__isnull=False).exclude(area="")
        if anio:
            salidas = salidas.filter(fecha_salida__year=anio)
        salidas = salidas.select_related("novedad")

        acumulado = {}
        for salida in salidas:
            clave = (
                salida.area,
                salida.fecha_salida.year,
                salida.fecha_salida.month,
            )
            acumulado[clave] = acumulado.get(clave, CERO) + salida.total_a_pagar

        por_area = {}
        for (area, anio_dia, mes), valor in acumulado.items():
            por_area.setdefault(area, []).append((anio_dia, mes, int(valor)))

        series = []
        for area, puntos in por_area.items():
            puntos.sort()  # cronológico: (anio, mes, valor)
            puntos_json = [
                [f"{mes}/1/{anio_dia}", valor] for anio_dia, mes, valor in puntos
            ]
            if area == InformeService.AREA_EJE_SECUNDARIO:
                series.append(
                    {
                        "name": area,
                        "yAxis": "a2",
                        "defaultPoint": {
                            "type": "line",
                            "marker": {
                                "size": 10,
                                "type": "circle",
                                "outline": {"color": "black", "width": 4},
                            },
                        },
                        "points": puntos_json,
                    }
                )
            else:
                series.append({"name": area, "points": puntos_json})
        return {"series": series}

    # ------------------------------------------------------------------ #
    # Informe mensual de salidas (F5-3, §5.7)
    # ------------------------------------------------------------------ #
    @staticmethod
    def mensual(mes, anio, filtros=None):
        """
        F5-3: salidas **NO eliminadas** del periodo `mes`/`anio` con filtros
        multidimensionales server-side (§5.7 — reemplaza el `consulta` del
        legacy, cuyo PHP `transporte_salida_controlador.php` no se tiene:
        el contrato estaba en el JS consumidor).

        `filtros` admite: `estado`, `sede`, `area`, `carpeta`, `search`.
        - La **fecha** es el periodo pedido (`mes`/`anio`); es la
          dimensión principal del informe de la sábana.
        - `estado` explícito manda (permite pedir incluso ELIMINADO);
          sin `estado` se excluyen las eliminadas (informe = lo vigente).
        - `search` cruza placa, cédula/nombre del conductor, área y
          observación (mismo alcance que `SalidaService.listar`, B1).

        Devuelve el queryset ya `select_related` y ordenado **día a día**
        (ascendente), como la tabla de la sábana.
        """
        mes, anio = validar_periodo(mes, anio)
        desde, hasta = rango_mes(mes, anio)
        filtros = filtros or {}

        queryset = (
            Salida.objects.select_related(
                "vehiculo", "conductor", "tecnico_asignado", "novedad"
            )
            .filter(fecha_salida__gte=desde, fecha_salida__lt=hasta)
        )

        estado = str(filtros.get("estado") or "").strip().upper()
        if estado:
            queryset = queryset.filter(estado=estado)
        else:
            queryset = queryset.exclude(estado=EstadoSalida.ELIMINADO)

        for campo in ("sede", "area", "carpeta"):
            valor = str(filtros.get(campo) or "").strip()
            if valor:
                queryset = queryset.filter(**{f"{campo}__iexact": valor})

        search = str(filtros.get("search") or "").strip()
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(vehiculo__placa__icontains=search)
                | Q(conductor__cedula__icontains=search)
                | Q(conductor__nombre_completo__icontains=search)
                | Q(area__icontains=search)
                | Q(observacion__icontains=search)
            )

        return queryset.order_by("fecha_salida", "id")

    @staticmethod
    def areas_del_periodo(mes, anio):
        """
        F5-3: áreas presentes en el periodo (`arr_areas` de la sábana) —
        sirve a la UI para poblar el filtro de área del mes.
        """
        mes, anio = validar_periodo(mes, anio)
        desde, hasta = rango_mes(mes, anio)
        return list(
            Salida.objects.filter(fecha_salida__gte=desde, fecha_salida__lt=hasta)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .exclude(area="")
            .filter(area__isnull=False)
            .values_list("area", flat=True)
            .distinct()
            .order_by("area")
        )

    # ------------------------------------------------------------------ #
    # Agregados de sábana (F5-7)
    # ------------------------------------------------------------------ #
    # Clave del contador de estado en el `arr_estado` del JS de la sábana:
    # "pendiente" es REPORTADO (JS 3007–3011).
    CLAVES_ESTADO = {
        EstadoSalida.APROBADO: "aprobado",
        EstadoSalida.VALIDADO: "validado",
        EstadoSalida.REPORTADO: "pendiente",
        EstadoSalida.RECHAZADO: "rechazado",
    }

    @staticmethod
    def _bloque_vacio():
        """Fila de agregado con las claves exactas del JS legacy."""
        return {
            "propios": 0,
            "externos": 0,
            "total_vehi": 0,
            "total_dia": 0,
            "arr_estado": {
                "aprobado": {"cnt": 0, "valor": 0},
                "validado": {"cnt": 0, "valor": 0},
                "pendiente": {"cnt": 0, "valor": 0},
                "rechazado": {"cnt": 0, "valor": 0},
                "total_est": {"cnt": 0, "valor": 0},
            },
        }

    @staticmethod
    def _acumular(bloque, salida, valor, contar=True):
        """
        Acumula una salida en un bloque de agregado (JS 2986–3154).

        `propios`/`externos`: EXTERNO es externo; PROPIO y RENTING son
        propios (`tipo_contrato !== 'EXTERNO'`). Los importes van en
        pesos enteros como el `parseInt` del legacy. `arr_estado` se
        acumula SIEMPRE (aunque `contar` sea False), como el legacy que
        filtraba los totales pero no el desglose de estados.
        """
        if contar:
            if salida.vehiculo.tipo_contrato == TipoContrato.EXTERNO:
                bloque["externos"] += 1
            else:
                bloque["propios"] += 1
            bloque["total_vehi"] += 1
            bloque["total_dia"] += valor
        clave = InformeService.CLAVES_ESTADO.get(salida.estado)
        if clave is not None:
            bloque["arr_estado"][clave]["cnt"] += 1
            bloque["arr_estado"][clave]["valor"] += valor
        bloque["arr_estado"]["total_est"]["cnt"] += 1
        bloque["arr_estado"]["total_est"]["valor"] += valor

    @staticmethod
    def _area_de(salida):
        """Área normalizada: mayúsculas y 'SIN AREA' (PHP 60 del legacy)."""
        return (salida.area or "").strip().upper() or "SIN AREA"

    @staticmethod
    def _carpeta_de(salida):
        """Carpeta normalizada con fallback 'SIN CARPETA' (JS 2983)."""
        return (salida.carpeta or "").strip() or "SIN CARPETA"

    @staticmethod
    def _agregar_area_carpeta(salidas, solo_aprobados=False):
        """
        Agrupa salidas en áreas con desglose por carpetas usando los
        contadores del JS de la sábana (`formatPlusRow`).

        `solo_aprobados` replica el interruptor de la sábana (JS 2910):
        los totales solo suman APROBADO/VALIDADO, pero `arr_estado`
        refleja todas las filas (el legacy acumulaba el desglose antes
        del filtro).
        """
        areas = {}
        for salida in salidas:
            nombre_area = InformeService._area_de(salida)
            nombre_carpeta = InformeService._carpeta_de(salida)
            valor = int(salida.total_a_pagar)
            contar = (not solo_aprobados) or salida.estado in (
                EstadoSalida.APROBADO,
                EstadoSalida.VALIDADO,
            )
            bloque_area = areas.setdefault(
                nombre_area,
                {
                    "area": nombre_area,
                    **InformeService._bloque_vacio(),
                    "_carpetas": {},
                },
            )
            InformeService._acumular(bloque_area, salida, valor, contar)
            bloque_carpeta = bloque_area["_carpetas"].setdefault(
                nombre_carpeta,
                {"carpeta": nombre_carpeta, **InformeService._bloque_vacio()},
            )
            InformeService._acumular(bloque_carpeta, salida, valor, contar)

        resultado = []
        for nombre_area in sorted(areas):
            bloque = areas[nombre_area]
            bloque["carpetas"] = [
                bloque["_carpetas"][c] for c in sorted(bloque["_carpetas"])
            ]
            del bloque["_carpetas"]
            resultado.append(bloque)
        return resultado

    @staticmethod
    def por_dia(fecha):
        """
        F5-7: agregado 'día a día' (`tb_trans_x_dia`) de UNA fecha —
        áreas con desglose por carpetas y contadores por estado.
        """
        if isinstance(fecha, str):
            fecha = date.fromisoformat(fecha)
        salidas = (
            Salida.objects.select_related("vehiculo", "novedad")
            .filter(fecha_salida=fecha)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .order_by("id")
        )
        return {
            "fecha": fecha.isoformat(),
            "areas": InformeService._agregar_area_carpeta(salidas),
        }

    @staticmethod
    def por_area(mes, anio, solo_aprobados=False):
        """
        F5-7: agregado del mes por área (`tb_trans_x_area`) con desglose
        por carpetas. `solo_aprobados` = interruptor de la sábana
        (totales solo APROBADO/VALIDADO).
        """
        mes, anio = validar_periodo(mes, anio)
        desde, hasta = rango_mes(mes, anio)
        salidas = (
            Salida.objects.select_related("vehiculo", "novedad")
            .filter(fecha_salida__gte=desde, fecha_salida__lt=hasta)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .order_by("fecha_salida", "id")
        )
        return {
            "mes": mes,
            "anio": anio,
            "areas": InformeService._agregar_area_carpeta(
                salidas, solo_aprobados=solo_aprobados
            ),
        }

    @staticmethod
    def areas_por_mes(anio):
        """
        F5-7: matriz área × meses del año (totales de salidas no
        eliminadas) — la base que el legacy descargaba como
        `areas_mes[year_month]` y que alimenta el gráfico F5-2.
        """
        try:
            anio = int(anio)
        except (TypeError, ValueError):
            raise ValueError("Año no válido.")
        if not 2000 <= anio <= 2100:
            raise ValueError("Año no válido.")

        salidas = (
            Salida.objects.select_related("vehiculo")
            .filter(fecha_salida__year=anio)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .order_by("fecha_salida", "id")
        )
        matriz = {}
        for salida in salidas:
            nombre_area = InformeService._area_de(salida)
            valor = int(salida.total_a_pagar)
            bloque = matriz.setdefault(nombre_area, {}).setdefault(
                salida.fecha_salida.month,
                {"propios": 0, "externos": 0, "total_vehi": 0, "total_dia": 0},
            )
            if salida.vehiculo.tipo_contrato == TipoContrato.EXTERNO:
                bloque["externos"] += 1
            else:
                bloque["propios"] += 1
            bloque["total_vehi"] += 1
            bloque["total_dia"] += valor

        return {
            "anio": anio,
            "areas": [
                {
                    "area": nombre_area,
                    "meses": [
                        {"mes": mes, **bloque}
                        for mes, bloque in sorted(meses.items())
                    ],
                }
                for nombre_area, meses in sorted(matriz.items())
            ],
        }

    @staticmethod
    def nomina(mes, anio):
        """
        F5-7: agregado de nómina (JS 4123–4346) — excluye REPORTADO y
        ELIMINADO; agrupa por (carpeta, placa); pagador leído del dato
        bancario vigente en SERVIDOR (CR-13); retefuente 1 %.

        El legacy agrupaba por `centro_costo` tomado de un mapa JS de
        carpetas (`map_carpetas[...].ccosto`); ese mapa vive en la BD de
        `common` (gate G3/B11) que aún no existe, así que el grupo es la
        CARPETA y `centro_costo` sale vacío hasta G3. `valor_dia` y
        `estado` son del primer día del grupo (orden placa, fecha).
        """
        mes, anio = validar_periodo(mes, anio)
        desde, hasta = rango_mes(mes, anio)
        salidas = (
            Salida.objects.select_related("vehiculo", "novedad")
            .filter(fecha_salida__gte=desde, fecha_salida__lt=hasta)
            .exclude(estado__in=(EstadoSalida.ELIMINADO, EstadoSalida.REPORTADO))
            .order_by("vehiculo__placa", "fecha_salida", "id")
        )
        consecutivos = dict(
            ConsecutivoMensual.objects.filter(mes=mes, anio=anio).values_list(
                "vehiculo_id", "consecutivo"
            )
        )
        grupos = {}
        pagadores = {}
        for salida in salidas:
            vehiculo = salida.vehiculo
            carpeta = InformeService._carpeta_de(salida)
            clave = (carpeta, vehiculo.placa)
            if vehiculo.pk not in pagadores:
                pagadores[vehiculo.pk] = InformeService._pagador(vehiculo)
            if clave not in grupos:
                pagador = pagadores[vehiculo.pk]
                grupos[clave] = {
                    "mes": mes,
                    "placa": vehiculo.placa,
                    "carpeta": carpeta,
                    # G3/B11: ccosto vendrá de `common` (map_carpetas).
                    "centro_costo": "",
                    "area": salida.area or "",
                    "tipo_contrato": vehiculo.tipo_contrato,
                    "cedula_pago": pagador["cedula_pago"],
                    "nombre_pago": pagador["nombre_pago"],
                    "total_dias": 0,
                    "valor_dia": int(salida.valor_dia),
                    "valor_base": CERO,
                    "estado": salida.estado,
                    "observacion": salida.observacion or "",
                    "consecutivo": consecutivos.get(vehiculo.pk, ""),
                }
            grupos[clave]["total_dias"] += 1
            grupos[clave]["valor_base"] += salida.total_a_pagar

        filas = []
        for clave in sorted(grupos):
            grupo = grupos[clave]
            rete = (grupo["valor_base"] * RETEFUENTE).quantize(Decimal("0.01"))
            grupo["rte"] = rete
            grupo["total_pagar"] = grupo["valor_base"] - rete
            filas.append(grupo)
        return {"mes": mes, "anio": anio, "filas": filas}

    @staticmethod
    def liquidacion_placa(mes, anio):
        """
        F5-7: liquidación por placa (JS 4267–4336) — una fila por
        vehículo: días, valor base (valor_dia ± novedad = total_a_pagar),
        retefuente 1 %, pagar, pagador y consecutivo si ya existe.
        Excluye REPORTADO y ELIMINADO como el legacy.
        """
        mes, anio = validar_periodo(mes, anio)
        desde, hasta = rango_mes(mes, anio)
        salidas = (
            Salida.objects.select_related("vehiculo", "novedad")
            .filter(fecha_salida__gte=desde, fecha_salida__lt=hasta)
            .exclude(estado__in=(EstadoSalida.ELIMINADO, EstadoSalida.REPORTADO))
            .order_by("vehiculo__placa", "fecha_salida", "id")
        )
        consecutivos = dict(
            ConsecutivoMensual.objects.filter(mes=mes, anio=anio).values_list(
                "vehiculo_id", "consecutivo"
            )
        )
        grupos = {}
        for salida in salidas:
            vehiculo = salida.vehiculo
            grupo = grupos.get(vehiculo.pk)
            if grupo is None:
                pagador = InformeService._pagador(vehiculo)
                grupos[vehiculo.pk] = {
                    "placa": vehiculo.placa,
                    "propietario": vehiculo.nombre_propietario or "SIN PROPIETARIO",
                    "tipo_contrato": vehiculo.tipo_contrato,
                    "total_dias": 0,
                    "valor_dia": int(salida.valor_dia),
                    "valor_base": CERO,
                    "cedula_pago": pagador["cedula_pago"],
                    "nombre_pago": pagador["nombre_pago"],
                    "tipo_cuenta": pagador["tipo_cuenta"],
                    "banco": pagador["banco"],
                    "cuenta_pago": pagador["cuenta_pago"],
                    "consecutivo": consecutivos.get(vehiculo.pk, ""),
                }
            grupos[vehiculo.pk]["total_dias"] += 1
            grupos[vehiculo.pk]["valor_base"] += salida.total_a_pagar

        filas = []
        for vehiculo_pk in sorted(grupos, key=lambda k: grupos[k]["placa"]):
            grupo = grupos[vehiculo_pk]
            rete = (grupo["valor_base"] * RETEFUENTE).quantize(Decimal("0.01"))
            grupo["rte"] = rete
            grupo["pagar"] = grupo["valor_base"] - rete
            filas.append(grupo)
        return {"mes": mes, "anio": anio, "filas": filas}

    # ------------------------------------------------------------------ #
    # Export server-side (F5-4, fila B4 / §5.7)
    # ------------------------------------------------------------------ #
    @staticmethod
    def exportar(queryset, formato="xlsx"):
        """
        F5-4: export **server-side** de un queryset de salidas (reemplaza
        el export client-side de DataTables, §5.7).

        Devuelve `(contenido, content_type, extension)`. `formato`:
        - `xlsx`: openpyxl, columnas de la sábana (números reales).
        - `csv`: separador `;` + BOM utf-8 — Excel en español abre los
          acentos y separa sin configuración adicional.
        """
        formato = str(formato or "xlsx").strip().lower()
        filas = InformeService._filas_export(queryset)
        if formato == "csv":
            return (
                InformeService._csv_export(filas),
                "text/csv; charset=utf-8",
                "csv",
            )
        if formato == "xlsx":
            return (
                InformeService._xlsx_export(filas),
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet",
                "xlsx",
            )
        raise ValueError("Formato no soportado: use xlsx o csv.")

    @staticmethod
    def _filas_export(queryset):
        """Cabecera + filas del export por salida (sin N+1)."""
        filas = []
        for salida in queryset.select_related("vehiculo", "conductor", "novedad"):
            novedad = getattr(salida, "novedad", None)
            filas.append(
                [
                    salida.fecha_salida.isoformat(),
                    salida.vehiculo.placa,
                    salida.conductor.cedula if salida.conductor else "",
                    salida.conductor.nombre_completo if salida.conductor else "",
                    salida.area or "",
                    salida.carpeta or "",
                    salida.sede or "",
                    str(salida.valor_dia),
                    novedad.tipo if novedad else "",
                    str(novedad.valor) if novedad else "",
                    str(salida.total_a_pagar),
                    salida.estado,
                    salida.observacion or "",
                ]
            )
        return [list(COLUMNAS_EXPORT)] + filas

    @staticmethod
    def _csv_export(filas):
        """CSV con `;` y BOM utf-8 (compatibilidad con Excel español)."""
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";")
        escritor.writerows(filas)
        return ("﻿" + buffer.getvalue()).encode("utf-8")

    @staticmethod
    def _xlsx_export(filas):
        """Libro XLSX con una hoja y los valores numéricos reales."""
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Transporte"
        for indice, fila in enumerate(filas):
            hoja.append(
                [
                    _a_numero(valor) if indice > 0 else valor
                    for valor in fila
                ]
            )
        salida = io.BytesIO()
        libro.save(salida)
        return salida.getvalue()
