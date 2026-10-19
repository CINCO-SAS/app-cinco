"""
PlanillaService — Planilla Oficial de Salida (§5.6 / CR-11 / S5).

Reemplaza del legacy (transporte_salida.php):
- generar_planilla_scope (POST → planilla_salida.php): determinaba las placas
  a incluir según el alcance y redirigía al formulario de impresión.
- planilla_salida.php: renderizaba el formato físico de despacho con QR,
  consecutivo y detalle de tripulación.

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
from datetime import date

from ..models import Salida, Vehiculo
from ..models.choices import EstadoSalida, TipoContrato
from .flota_service import FlotaService
from .liquidacion_service import LiquidacionService


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
                salidas del día, consecutivo y ruta_qr.
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
