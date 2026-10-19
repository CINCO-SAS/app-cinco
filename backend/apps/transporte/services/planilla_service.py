"""
PlanillaService — Planilla Oficial de Salida (§5.6 / CR-11 / S5).

Reemplaza del legacy (transporte_salida.php):
- generar_planilla_scope (POST → planilla_salida.php): determinaba las placas
  a incluir según el alcance y redirigía al formulario de impresión.
- planilla_salida.php: renderizaba el formato físico de despacho (F-104) con
  QR, consecutivo y detalle de tripulación → ahora `html_formato`
  (GET/POST `/planillas/formato/`), P1 cerrado con el archivo verificado.

CR-11 — Filtro duro: las motos (TipoVehiculo.*) no existen en choices, pero
la exclusión es sobre tipo_contrato PROPIO/EXTERNO/RENTING vs una lista de
placas. Toda planilla excluye vehículos cuyo tipo_vehiculo sea 'MOTO'
(no está en los choices, pero el valor puede venir de datos legacy);
y en cualquier caso solo aplica a la flota automotor de 4+ ruedas.

Alcances soportados (legacy strtoupper($alcance)):
- 'PLACA'    → un solo vehículo por placa exacta.
- 'PROPIO'   → todos los vehículos con tipo_contrato=PROPIO activos.
- 'EXTERNO'  → todos con tipo_contrato=EXTERNO activos.
- 'RENTING'  → todos con tipo_contrato=RENTING activos.
- 'TODAS'    → todos los vehículos activos (PROPIO + EXTERNO + RENTING).

Para cada vehículo resuelto la planilla devuelve:
1. Datos del vehículo y conductor habitual.
2. Salidas del día indicado (estado != ELIMINADO).
3. Consecutivo mensual: se GENERA si no existe (proximo_consecutivo atómico).
4. Ruta del QR del vehículo (Vehiculo.codigo_qr).
"""
import base64
import calendar
from datetime import date
from html import escape

from ..models import Salida, Vehiculo
from ..models.choices import EstadoSalida, TipoContrato
from .flota_service import FlotaService
from .informe_service import EMPRESA, NIT
from .liquidacion_service import LiquidacionService


# Rótulos del formato F-104 (meses en mayúsculas, como el legacy).
MESES_F104 = (
    "", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
)

_TEXTO_RECOMENDACION = (
    "TE RECOMENDAMOS HACER FIRMAR CADA DÍA LA PLANILLA POR LOS PORTEROS "
    "ASIGNADOS DE CINCO S.A.S. EN LOS ESPACIOS DE FIRMA SALIDA Y FIRMA "
    "RETORNO, YA QUE ESTOS ESPACIOS EN BLANCO NO SE PAGARÁN AL FINALIZAR "
    "EL MES. GRACIAS"
)


def _esc(valor):
    """Escapa cualquier valor imprimible (incluida entrada del usuario)."""
    return escape(str(valor if valor is not None else ""))


def _campo(etiqueta, valor="", clase=""):
    """Casilla del encabezado F-104: rótulo + valor.

    Valor vacío = casilla que se diligencia a mano (TOTAL DÍAS,
    DESCUENTOS, ADICIONALES y VALOR TOTAL, como en el legacy).
    """
    return (
        f'<div class="campo">{_esc(etiqueta)}'
        f'<span class="valor {_esc(clase)}">{valor}</span></div>'
    )


# Alcances válidos (espejo del front legacy).
ALCANCE_PLACA = "PLACA"
ALCANCE_TODAS = "TODAS"
ALCANCES_CONTRATO = {
    "PROPIO": TipoContrato.PROPIO,
    "EXTERNO": TipoContrato.EXTERNO,
    "RENTING": TipoContrato.RENTING,
}
ALCANCES_VALIDOS = {ALCANCE_PLACA, ALCANCE_TODAS} | set(ALCANCES_CONTRATO)


class PlanillaService:
    """Genera el payload de la Planilla Oficial de Salida."""

    # ------------------------------------------------------------------ #
    # Punto de entrada principal
    # ------------------------------------------------------------------ #
    @staticmethod
    def generar_planilla(fecha, alcance, placa=None, actor=None):
        """Construye la planilla para los vehículos determinados por el alcance.

        Args:
            fecha (str | date): Fecha de la planilla (YYYY-MM-DD o date).
            alcance (str): 'PLACA' | 'PROPIO' | 'EXTERNO' | 'RENTING' | 'TODAS'.
            placa (str | None): Obligatoria si alcance == 'PLACA'.
            actor: Instancia Empleado que genera la planilla (para auditoría del consecutivo).

        Returns:
            dict con:
              - fecha (date)
              - alcance (str)
              - vehiculos (list[dict]): una entrada por vehículo con datos,
                salidas del día, consecutivo, valor_día y ruta_qr.
        """
        fecha = PlanillaService._validar_fecha(fecha)
        alcance = PlanillaService._validar_alcance(alcance, placa)
        vehiculos_qs = PlanillaService._resolver_vehiculos(alcance, placa)

        filas = []
        for vehiculo in vehiculos_qs.select_related(
            "conductor_habitual"
        ).order_by("placa"):
            fila = PlanillaService._construir_fila(vehiculo, fecha, actor)
            filas.append(fila)

        if not filas:
            raise ValueError(
                f"No se encontraron vehículos activos para el alcance '{alcance}'."
            )

        return {
            "fecha": fecha,
            "alcance": alcance,
            "vehiculos": filas,
        }

    # ------------------------------------------------------------------ #
    # Resolución de vehículos por alcance (CR-11)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolver_vehiculos(alcance, placa):
        """Devuelve el queryset base de vehículos según el alcance.

        CR-11 — filtro excluyente duro (legacy `transporte_salida.php`
        597/608/663: ``AND tipo != 'MOTO'``): aunque los choices de
        ``TipoVehiculo`` no incluyen MOTO, la carga histórica (ETL) puede
        traer ese valor en filas viejas, así que el filtro se aplica de
        forma explícita en TODOS los alcances, como en el legacy.
        Solo aplica a flota automotor de 4+ ruedas (D-A13).
        """
        qs = Vehiculo.objects.filter(activo=True).exclude(
            tipo_vehiculo__iexact="MOTO"
        )

        if alcance == ALCANCE_PLACA:
            qs = qs.filter(placa=placa.upper())
            if not qs.exists():
                raise ValueError(
                    f"No existe un vehículo activo con placa '{placa}'."
                )
            return qs

        if alcance == ALCANCE_TODAS:
            return qs

        # Alcance por tipo de contrato (PROPIO / EXTERNO / RENTING).
        tipo_contrato = ALCANCES_CONTRATO[alcance]
        return qs.filter(tipo_contrato=tipo_contrato)

    # ------------------------------------------------------------------ #
    # Construcción de la fila de un vehículo
    # ------------------------------------------------------------------ #
    @staticmethod
    def _construir_fila(vehiculo, fecha, actor):
        """Datos de un vehículo para la planilla.

        Genera el consecutivo atómico si aún no existe para el período
        (año y mes de la fecha solicitada).
        """
        mes = fecha.month
        anio = fecha.year

        # Consecutivo mensual atómico (idempotente si ya existe).
        consecutivo_obj, creado = LiquidacionService.proximo_consecutivo(
            vehiculo.pk, mes, anio, actor=actor
        )

        # Salidas del día (estado != ELIMINADO).
        salidas_dia = list(
            Salida.objects.filter(
                vehiculo=vehiculo,
                fecha_salida=fecha,
            )
            .exclude(estado=EstadoSalida.ELIMINADO)
            .select_related("conductor", "tecnico_asignado")
            .order_by("creado_en")
        )

        # Conductor habitual del vehículo.
        conductor = vehiculo.conductor_habitual
        conductor_datos = None
        if conductor:
            conductor_datos = {
                "cedula": conductor.cedula,
                "nombre": conductor.nombre_completo,
                "celular": conductor.celular,
                "licencia_categoria": conductor.licencia_categoria,
                "licencia_vencimiento": conductor.licencia_vencimiento,
            }

        # Salidas serializadas (datos mínimos para el formato físico).
        salidas_datos = []
        for salida in salidas_dia:
            # El técnico asignado es personal de nómina (FK Empleado
            # cross-DB); el formato físico imprime la CÉDULA, no el id.
            tecnico = salida.tecnico_asignado
            salidas_datos.append(
                {
                    "id": salida.pk,
                    "estado": salida.estado,
                    "conductor_cedula": (
                        salida.conductor.cedula if salida.conductor_id else None
                    ),
                    "tecnico_cedula": (
                        tecnico.cedula if tecnico is not None else None
                    ),
                    "area": salida.area,
                    "carpeta": salida.carpeta,
                    "observacion": salida.observacion,
                }
            )

        qr_file = FlotaService.obtener_ruta_qr(vehiculo.pk)

        return {
            "vehiculo_id": vehiculo.pk,
            "placa": vehiculo.placa,
            "tipo_vehiculo": vehiculo.tipo_vehiculo,
            "tipo_contrato": vehiculo.tipo_contrato,
            "marca": vehiculo.marca,
            "referencia": vehiculo.referencia,
            "modelo_anio": vehiculo.modelo_anio,
            "color": vehiculo.color,
            "nombre_propietario": vehiculo.nombre_propietario,
            "cedula_propietario": vehiculo.cedula_propietario,
            "valor_dia_base": vehiculo.valor_dia_base,
            "conductor": conductor_datos,
            "consecutivo": consecutivo_obj.consecutivo,
            "consecutivo_creado": creado,
            "mes": mes,
            "anio": anio,
            "ruta_qr": qr_file.name if qr_file else None,
            "salidas_del_dia": salidas_datos,
        }

    # ------------------------------------------------------------------ #
    # Validaciones internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_fecha(fecha):
        if isinstance(fecha, date):
            return fecha
        if not fecha:
            raise ValueError("La fecha de la planilla es obligatoria.")
        try:
            return date.fromisoformat(str(fecha).strip())
        except ValueError:
            raise ValueError(
                f"Fecha inválida: '{fecha}'. Use el formato YYYY-MM-DD."
            )

    @staticmethod
    def _validar_alcance(alcance, placa):
        alcance = (alcance or ALCANCE_PLACA).upper().strip()
        if alcance not in ALCANCES_VALIDOS:
            raise ValueError(
                f"Alcance '{alcance}' inválido. "
                f"Valores aceptados: {sorted(ALCANCES_VALIDOS)}."
            )
        if alcance == ALCANCE_PLACA and not placa:
            raise ValueError(
                "La placa es obligatoria cuando el alcance es 'PLACA'."
            )
        return alcance

    # ------------------------------------------------------------------ #
    # Formato físico F-104 (P1 — legacy `planilla_salida.php`)
    # ------------------------------------------------------------------ #
    @staticmethod
    def html_formato(planilla):
        """HTML imprimible del formato F-104: una hoja por vehículo.

        Reemplaza `planilla_salida.php`: el navegador abre el documento y
        lo imprime en **LETTER horizontal**, con salto de página por
        vehículo (una planilla por hoja, como el legacy).

        Mejoras registradas sobre el legacy (no se replican sus rarezas):
        - **FECHA real** de impresión; el legacy imprimía "16/02/2022" fijo.
        - **CONDUCTOR y TELÉFONO reales**: la consulta del legacy a
          `nokia_base_infraestructura` estaba *comentada*, así que esas dos
          casillas salían vacías.
        - **VALOR DÍA real**: el legacy lo consultaba y ni lo imprimía.
        - **CONSECUTIVO mensual impreso** (PLAN_TECNICO §3.6 lo exige; el
          formato legacy no lo mostraba).
        - **Sin código de barras**: D-A8 lo eliminó como artefacto
          regenerable; el QR es el único código de verificación y la casilla
          de la placa imprime la placa en grande.
        - **Autocontenido**: QR embebido en base64 y sin CDNs externos, así
          imprime igual con la red caída (el legacy dependía de Bootstrap y
          FontAwesome remotos y de un PNG en disco).
        - **Todo valor escapado** con `html.escape` (el legacy imprimía
          entrada del usuario sin escapar).

        TOTAL DÍAS / DESCUENTOS / ADICIONALES / VALOR TOTAL quedan EN BLANCO:
        se diligencian a mano durante el mes (el importe se liquida en la
        sábana, no en el despacho), igual que en el formato original.
        """
        fecha = planilla["fecha"]
        mes_nombre = MESES_F104[fecha.month]
        ultimo = calendar.monthrange(fecha.year, fecha.month)[1]

        hojas = "\n".join(
            PlanillaService._hoja_vehiculo(fila, fecha, mes_nombre, ultimo)
            for fila in planilla["vehiculos"]
        )
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>F-104 Planilla de Salida</title>
<style>
@page {{ size: LETTER landscape; margin: 6mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #000; }}
.hoja {{ page-break-after: always; }}
.hoja:last-child {{ page-break-after: auto; }}
.fila {{ display: flex; border: 1px solid #000; margin: 1px; }}
.celda {{ border: 1px solid #000; padding: 4px; text-align: center;
          font-size: 11px; display: flex; align-items: center;
          justify-content: center; }}
.papel {{ width: 25%; flex-direction: column; }}
.titulo {{ width: 50%; font-weight: bold; }}
.meta {{ width: 25%; flex-direction: column; padding: 0; }}
.meta div {{ flex: 1; width: 100%; display: flex; align-items: center;
             justify-content: center; border-bottom: 1px solid #000; }}
.meta div:last-child {{ border-bottom: 0; }}
.bloque {{ border: 1px solid #000; margin: 1px; margin-top: -1px;
           text-align: center; padding: 3px; }}
.periodo {{ font-size: 14px; font-weight: bold; }}
.nota {{ font-size: 11px; }}
.cuerpo {{ display: flex; border: 1px solid #000; margin: 1px; margin-top: -1px; }}
.campos {{ width: 75%; display: grid; grid-template-columns: repeat(3, 1fr); }}
.campo {{ border-right: 1px solid #000; border-bottom: 1px solid #000;
          padding: 3px 6px; min-height: 34px; font-size: 11px; text-align: left; }}
.campos .campo:nth-child(3n) {{ border-right: 0; }}
.campo .valor {{ display: block; font-weight: bold; font-size: 13px;
                 text-align: center; }}
.campo .valor.placa {{ font-size: 18px; letter-spacing: 3px; }}
.qr {{ width: 25%; padding: 4px; }}
.qr img {{ width: 185px; height: 185px; }}
table.registro {{ width: 100%; border-collapse: collapse; margin-top: -1px; }}
table.registro th, table.registro td {{ border: 1px solid #000; font-size: 11px;
                                        padding: 5px; text-align: center;
                                        height: 28px; }}
.nowrap {{ white-space: nowrap; }}
.vacio {{ border: 0 !important; }}
</style>
</head>
<body>
{hojas}
</body>
</html>"""

    @staticmethod
    def _hoja_vehiculo(fila, fecha, mes_nombre, ultimo):
        """Una hoja del formato F-104 (encabezado + tabla de firmas)."""
        conductor = fila.get("conductor") or {}
        qr_png = FlotaService.generar_qr(fila["vehiculo_id"])
        qr_b64 = base64.b64encode(qr_png).decode("ascii")

        # Tabla de 2 bloques de 7 columnas (16 filas): los días 1..16 a la
        # izquierda y 17..último a la derecha; como en el legacy, las celdas
        # de un día inexistente se imprimen sin borde.
        encabezado = (
            "<th>DÍA</th><th>HORA SALIDA</th><th class=\"nowrap\">FIRMA SALIDA</th>"
            "<th>MÓVILES TRANSPORTADAS</th><th>HORA LLEGADA</th>"
            "<th class=\"nowrap\">FIRMA RETORNO</th><th>OBSERVACIÓN</th>"
        ) * 2

        filas = []
        for dia in range(1, 17):
            dia_derecha = dia + 16
            if dia_derecha <= ultimo:
                derecha = (
                    f"<td>{dia_derecha}</td>"
                    + "<td></td>" * 6
                )
            else:
                derecha = "<td class=\"vacio\"></td>" * 7
            filas.append(
                f"<tr><td>{dia}</td>" + "<td></td>" * 6 + derecha + "</tr>"
            )

        return f"""<section class="hoja">
<div class="fila">
<div class="celda papel">{_esc(EMPRESA)}<br /><small>NIT {_esc(NIT)}</small></div>
<div class="celda titulo">F-104 PLANILLA CONTROL DE VEHÍCULOS CINCO S.A.S MENSUAL</div>
<div class="celda meta">
<div>VERSIÓN: 01</div>
<div>FECHA: {_esc(fecha.strftime("%d/%m/%Y"))}</div>
<div>CONSECUTIVO: {_esc(fila["consecutivo"])}</div>
</div>
</div>
<div class="bloque periodo">DEL 01 DE {mes_nombre} AL {ultimo} DE {mes_nombre} DE {_esc(fecha.year)}</div>
<div class="bloque nota">{_TEXTO_RECOMENDACION}</div>
<div class="cuerpo">
<div class="campos">
{_campo("CONDUCTOR:", _esc(conductor.get("nombre")))}
{_campo("PROPIETARIO:", _esc(fila["nombre_propietario"]))}
{_campo("TELÉFONO/CELULAR:", _esc(conductor.get("celular")))}
{_campo("PLACA:", _esc(fila["placa"]), clase="placa")}
{_campo("VALOR DÍA:", PlanillaService._dinero(fila["valor_dia_base"]))}
{_campo("TOTAL DÍAS:")}
{_campo("DESCUENTOS:")}
{_campo("ADICIONALES:")}
{_campo("VALOR TOTAL:")}
</div>
<div class="celda qr"><img alt="QR {_esc(fila["placa"])}" src="data:image/png;base64,{qr_b64}" /></div>
</div>
<div class="bloque nota">POR FAVOR DILIGENCIAR LA SIGUIENTE PLANILLA CON LETRA LEGIBLE</div>
<table class="registro">
<thead><tr>{encabezado}</tr></thead>
<tbody>
{"".join(filas)}
</tbody>
</table>
</section>"""

    @staticmethod
    def _dinero(valor):
        """'$ 85.000' — importe con separador de miles para el formato."""
        return f"$ {int(valor):,}".replace(",", ".")
