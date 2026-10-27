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
from .contacto_service import ContactoService
from .flota_service import FlotaService
from .informe_service import EMPRESA, NIT
from .liquidacion_service import LiquidacionService
from .logo_b64 import LOGO_CINCO_B64


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
            .select_related("conductor")
            # Cross-BD: tecnico_asignado vive en azul (Empleado); un
            # select_related sería un JOIN imposible para Django (1146).
            .prefetch_related("tecnico_asignado")
            .order_by("creado_en")
        )

        # Conductor habitual del vehículo.
        conductor = vehiculo.conductor_habitual
        conductor_datos = None
        if conductor:
            celular_mostrar = conductor.celular
            try:
                contacto = ContactoService.contacto_conductor(conductor.pk)
                celular_mostrar = (
                    contacto.get("celular_personal")
                    or contacto.get("celular_alterno")
                    or conductor.celular
                    or ""
                )
            except Exception:
                pass

            conductor_datos = {
                "cedula": conductor.cedula,
                "nombre": conductor.nombre_completo,
                "celular": celular_mostrar,
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
    # Formato físico F-104 (Idéntico al legacy `planilla_salida.php`)
    # ------------------------------------------------------------------ #
    @staticmethod
    def html_formato(planilla):
        """HTML imprimible del formato F-104: réplica visual idéntica al legacy.

        Diseño y estructura exactos a `planilla_salida.php`:
        - Logotipo oficial de Cinco S.A.S en esquina superior izquierda.
        - Título central F-104 PLANILLA CONTROL DE VEHÍCULOS CINCO S.A.S MENSUAL.
        - Cuadro de VERSIÓN: 01 y FECHA.
        - Período mensual destacado.
        - Texto de advertencia/recomendación a porteros.
        - Rejilla superior de datos del vehículo:
          * Columna 1 (6/12): CONDUCTOR, PROPIETARIO, TELÉFONO/CELULAR.
          * Columna 2 (3/12): PLACA, VALOR DÍA, TOTAL DÍAS.
          * Columna 3 (3/12): DESCUENTOS, ADICIONALES, VALOR TOTAL.
          * Columna indicación inferior de diligenciar en letra legible.
        - Código QR a la derecha ocupando toda la altura de la sección.
        - Tabla de firmas de 31 días dividida exactamente en dos bloques (1..16 y 17..último)
          con encabezados DÍA, HORA SALIDA, FIRMA SALIDA, MÓVILES TRANSPORTADAS,
          HORA LLEGADA, FIRMA RETORNO, OBSERVACIÓN.
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
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0" />
<title>Planilla Salida</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" />
<style>
  @page {{
    size: LETTER landscape;
    margin: 4mm 6mm;
  }}
  * {{
    box-sizing: border-box;
  }}
  body {{
    margin: 0;
    padding: 0;
    background: #fff;
    color: #000;
    font-family: Arial, Helvetica, sans-serif;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  p:not(.info-text) {{
    font-size: 11px;
    margin: 0;
  }}
  .info-text {{
    font-size: 13px !important;
  }}
  .row-content {{
    margin: 1px;
    border: 1px solid #000;
  }}
  .logo {{
    height: 48px;
    max-width: 100%;
    object-fit: contain;
  }}
  .periodo {{
    margin: 2px 0 !important;
    font-size: 15px;
    font-weight: bold;
  }}
  .info {{
    height: 34px;
    position: relative;
    padding: 2px 6px;
    text-align: left;
  }}
  .info p.rotulo {{
    font-size: 10px;
    font-weight: 500;
    margin: 0;
  }}
  .info .info-text {{
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    top: 12px;
    width: 90%;
    text-align: center;
    font-weight: bold;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .info .info-text.placa-text {{
    font-size: 16px !important;
    letter-spacing: 2px;
  }}
  .qr-container {{
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
    padding: 2px;
  }}
  .qr {{
    width: 175px;
    height: 175px;
    object-fit: contain;
  }}
  table.table-planilla {{
    width: 100%;
    border-collapse: collapse;
    margin: 0;
  }}
  table.table-planilla th,
  table.table-planilla td {{
    border: 1px solid #000 !important;
    font-size: 10px;
    padding: 3.5px 2px !important;
    text-align: center;
    vertical-align: middle;
    height: 25px;
  }}
  table.table-planilla th {{
    font-weight: bold;
  }}
  .border-0-custom {{
    border: 0 !important;
  }}
  @media print {{
    .container-fluid {{
      page-break-after: always;
      break-after: page;
    }}
    .container-fluid:last-child {{
      page-break-after: auto;
      break-after: auto;
    }}
  }}
</style>
</head>
<body>
{hojas}
</body>
</html>"""

    @staticmethod
    def _hoja_vehiculo(fila, fecha, mes_nombre, ultimo):
        """Una hoja del formato F-104 idéntica a la estructura de `planilla_salida.php`."""
        conductor = fila.get("conductor") or {}
        qr_png = FlotaService.generar_qr(fila["vehiculo_id"])
        qr_b64 = base64.b64encode(qr_png).decode("ascii")

        # Filas de la tabla de 1 a 16 (izquierda) y 17 a 31/32 (derecha)
        rows_html = []
        for dia in range(1, 17):
            dia_der = dia + 16
            if dia_der <= ultimo:
                der_cells = (
                    f"<td>{dia_der}</td>"
                    "<td></td><td></td><td></td><td></td><td></td><td></td>"
                )
            else:
                der_cells = (
                    '<td class="border-0-custom"></td>' * 7
                )
            rows_html.append(
                f"<tr>"
                f"<td>{dia}</td>"
                f"<td></td><td></td><td></td><td></td><td></td><td></td>"
                f"{der_cells}"
                f"</tr>"
            )

        nombre_conductor = _esc(conductor.get("nombre"))
        nombre_propietario = _esc(fila.get("nombre_propietario"))
        celular = _esc(conductor.get("celular"))
        placa = _esc(fila.get("placa"))
        valor_dia = PlanillaService._dinero(fila["valor_dia_base"]) if fila.get("valor_dia_base") else ""

        return f"""<div class="container-fluid p-0">
  <div class="row row-content m-1 border border-dark">
    <!-- LOGO -->
    <div class="col-3 border-end border-dark p-1 text-center d-flex align-items-center justify-content-center">
      <img class="img-fluid logo" src="{LOGO_CINCO_B64}" alt="Cinco S.A.S" />
    </div>

    <!-- TÍTULO -->
    <div class="col-6 border-end border-dark d-flex align-items-center justify-content-center p-0">
      <p class="m-0 text-center fw-bold fs-6">F-104 PLANILLA CONTROL DE VEHÍCULOS CINCO S.A.S MENSUAL</p>
    </div>

    <!-- VERSIÓN - FECHA - CONSECUTIVO -->
    <div class="col-3 p-0">
      <div class="col-12 border-bottom border-dark d-flex align-items-center justify-content-center" style="height: 18px;">
        <p class="m-0 text-center fw-semibold" style="font-size: 10px;">VERSIÓN: 01</p>
      </div>
      <div class="col-12 border-bottom border-dark d-flex align-items-center justify-content-center" style="height: 18px;">
        <p class="m-0 text-center fw-semibold" style="font-size: 10px;">FECHA: {_esc(fecha.strftime("%d/%m/%Y"))}</p>
      </div>
      <div class="col-12 d-flex align-items-center justify-content-center" style="height: 18px;">
        <p class="m-0 text-center fw-semibold" style="font-size: 10px;">CONSECUTIVO: {_esc(fila.get("consecutivo", ""))}</p>
      </div>
    </div>

    <!-- RECOMENDACIONES - INFO -->
    <div class="col-9 border-top border-end border-dark p-0">
      <!-- PERÍODO -->
      <div class="col-12 border-bottom border-dark p-0">
        <h5 class="m-0 text-center periodo py-1">DEL 01 DE {mes_nombre} AL {ultimo} DE {mes_nombre} DE {_esc(fecha.year)}</h5>
      </div>
      <div class="col-12 border-bottom border-dark d-flex align-items-center justify-content-center px-2 py-1" style="min-height: 28px;">
        <p class="m-0 text-center" style="font-size: 10px; line-height: 1.2;">
          {_TEXTO_RECOMENDACION}
        </p>
      </div>

      <!-- CAMPOS DEL VEHÍCULO Y CONDUCTOR -->
      <div class="col-12 d-flex flex-wrap p-0">
        <div class="col-6 border-end border-dark d-grid p-0">
          <div class="col-12 info">
            <p class="rotulo">CONDUCTOR:</p>
            <p class="fw-bold info-text">{nombre_conductor}</p>
          </div>
          <div class="col-12 border-top border-dark info">
            <p class="rotulo">PROPIETARIO:</p>
            <p class="fw-bold info-text">{nombre_propietario}</p>
          </div>
          <div class="col-12 border-top border-dark info">
            <p class="rotulo">TELÉFONO/CELULAR:</p>
            <p class="fw-bold info-text">{celular}</p>
          </div>
        </div>

        <div class="col-3 border-end border-dark d-grid p-0">
          <div class="col-12 info">
            <p class="rotulo">PLACA:</p>
            <p class="fw-bold info-text placa-text">{placa}</p>
          </div>
          <div class="col-12 border-top border-dark info">
            <p class="rotulo">VALOR DÍA:</p>
            <p class="fw-bold info-text">{valor_dia}</p>
          </div>
          <div class="col-12 border-top border-dark info">
            <p class="rotulo">TOTAL DÍAS:</p>
            <p class="fw-bold info-text"></p>
          </div>
        </div>

        <div class="col-3 d-grid p-0">
          <div class="col-12 info">
            <p class="rotulo">DESCUENTOS:</p>
            <p class="fw-bold info-text"></p>
          </div>
          <div class="col-12 border-top border-dark info">
            <p class="rotulo">ADICIONALES:</p>
            <p class="fw-bold info-text"></p>
          </div>
          <div class="col-12 border-top border-dark info">
            <p class="rotulo">VALOR TOTAL:</p>
            <p class="fw-bold info-text"></p>
          </div>
        </div>

        <!-- INDICACIONES -->
        <div class="col-12 border-top border-dark d-flex align-items-center justify-content-center py-1">
          <p class="m-0 text-center fw-semibold" style="font-size: 10px;">
            POR FAVOR DILIGENCIAR LA SIGUIENTE PLANILLA CON LETRA LEGIBLE
          </p>
        </div>
      </div>
    </div>

    <!-- QR CONTAINER -->
    <div class="col-3 border-top border-dark p-0 text-center qr-container" id="qr-container">
      <img src="data:image/png;base64,{qr_b64}" class="img-fluid qr" alt="QR {placa}" />
    </div>

    <!-- TABLA DE FIRMAS (DÍAS 1 AL 31) -->
    <div class="col-12 p-0 border-top border-dark">
      <table class="table-planilla">
        <thead>
          <tr>
            <th style="width: 4%;">DÍA</th>
            <th style="width: 7%;">HORA SALIDA</th>
            <th style="width: 8%;" class="text-nowrap">FIRMA SALIDA</th>
            <th style="width: 11%;">MÓVILES TRANSPORTADAS</th>
            <th style="width: 7%;">HORA LLEGADA</th>
            <th style="width: 8%;" class="text-nowrap">FIRMA RETORNO</th>
            <th style="width: 5%;">OBSERVACIÓN</th>
            <th style="width: 4%;">DÍA</th>
            <th style="width: 7%;">HORA SALIDA</th>
            <th style="width: 8%;" class="text-nowrap">FIRMA SALIDA</th>
            <th style="width: 11%;">MÓVILES TRANSPORTADAS</th>
            <th style="width: 7%;">HORA LLEGADA</th>
            <th style="width: 8%;" class="text-nowrap">FIRMA RETORNO</th>
            <th style="width: 5%;">OBSERVACIÓN</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_html)}
        </tbody>
      </table>
    </div>
  </div>
</div>"""

    @staticmethod
    def _dinero(valor):
        """'$ 85.000' — importe con separador de miles para el formato."""
        return f"$ {int(valor):,}".replace(",", ".")

