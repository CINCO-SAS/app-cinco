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
from decimal import Decimal
from html import escape

from ..models import (
    ConsecutivoMensual,
    DatosBancariosVehiculo,
    Salida,
    Vehiculo,
)
from ..models.choices import EstadoSalida
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


class InformeService:
    """Única capa de reglas de informes (Tab 2) del módulo transporte."""

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
                vehiculo=vehiculo, fecha_salida__range=(desde, hasta)
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
