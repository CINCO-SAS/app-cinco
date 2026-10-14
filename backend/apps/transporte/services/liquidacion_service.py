"""
LiquidacionService — núcleo de liquidaciones del Tab 3 (§5.2).

Reemplaza del legacy (base_salida_transporte.php):
- vehiculos_pago_mensual (388–468)  → sabana_pago_mensual
- vehiculos_pronto_pago (312–387)   → sabana_pronto_pago
- obtenerConsecutivoYRegistrar (234–289) → proximo_consecutivo atómico
- gate de edición tras la fecha límite (cerrar_mes, B3 / permiso
  transporte.editar_tras_cierre)

CR-10 — criterios de estado diferenciados:
- Pago mensual suma APROBADO + REPORTADO + VALIDADO (línea 399).
- Pronto pago suma EXCLUSIVAMENTE APROBADO (línea 322).
- Retroceso histórico: si el período pedido es el ACTUAL y no hay vehículos
  inscritos, se retroceden hasta 6 meses buscando la última vigencia
  parametrizada (331–348 / 411–428). El legacy devolvía `new_mes`/`new_yyyy`
  con el período realmente usado; aquí es `mes_aplicado`/`anio_aplicado`.

Fórmula única (§5.1): total = Σ salida.total_a_pagar (valor_dia ± novedad)
sobre las salidas del período en los estados de la modalidad.

Nota (D2/B3): la gestión de las filas FechaLimiteCierre vive en
ParametrosService (A1); aquí está el gate de lectura/escritura
`puede_editar_periodo`. La ruta compuesta /cierres/{mes}/{anio}/ (matriz B3)
queda pendiente.
"""
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction

from ..models import (
    ConsecutivoMensual,
    FechaLimiteCierre,
    PagoVehiculoMensual,
    Salida,
    Vehiculo,
)
from ..models.choices import EstadoSalida, TipoPago
from .periodos import (
    entero,
    es_periodo_actual,
    rango_mes,
    restar_meses,
    validar_anio,
    validar_mes,
    validar_periodo,
)

# CR-10: estados que suman en cada modalidad — una sola fuente de verdad.
ESTADOS_POR_TIPO = {
    TipoPago.MENSUAL: (
        EstadoSalida.APROBADO,
        EstadoSalida.REPORTADO,
        EstadoSalida.VALIDADO,
    ),
    TipoPago.PRONTO_PAGO: (EstadoSalida.APROBADO,),
}

# Retroceso histórico máximo (CR-10: "retrospectiva de 6 meses").
RETROCESO_MAXIMO = 6

# Consecutivo inicial del legacy (obtenerConsecutivoYRegistrar, línea 284).
CONSECUTIVO_INICIAL = 1000

CERO = Decimal("0.00")


class LiquidacionService:
    """Única capa de reglas de liquidaciones del módulo transporte."""

    # ------------------------------------------------------------------ #
    # Listado de pagos (D3)
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar_pagos(query_params=None):
        """Inscripciones/marcas de pago (D3): filtros mes, anio, tipo,
        vehiculo, placa. Devuelve queryset paginable."""
        queryset = (
            PagoVehiculoMensual.objects.select_related("vehiculo")
            .order_by("-anio", "-mes", "vehiculo__placa")
        )
        query_params = query_params or {}

        mes = query_params.get("mes")
        if mes not in (None, ""):
            queryset = queryset.filter(mes=validar_mes(entero(mes, "mes")))

        anio = query_params.get("anio")
        if anio not in (None, ""):
            queryset = queryset.filter(anio=validar_anio(entero(anio, "anio")))

        tipo = query_params.get("tipo")
        if tipo not in (None, ""):
            if tipo not in TipoPago.values:
                raise ValueError(
                    f"El tipo de pago '{tipo}' no es un valor válido."
                )
            queryset = queryset.filter(tipo=tipo)

        vehiculo = query_params.get("vehiculo")
        if vehiculo not in (None, ""):
            queryset = queryset.filter(
                vehiculo_id=entero(vehiculo, "vehiculo")
            )

        return queryset

    # ------------------------------------------------------------------ #
    # Sábanas de pago (D4 / CR-10)
    # ------------------------------------------------------------------ #
    @staticmethod
    def sabana_pago_mensual(mes, anio, filtros=None):
        """Sábana de pago mensual: APROBADO + REPORTADO + VALIDADO."""
        return LiquidacionService._sabana(mes, anio, TipoPago.MENSUAL, filtros)

    @staticmethod
    def sabana_pronto_pago(mes, anio, filtros=None):
        """Pronto pago (modalidad anticipada): exclusivamente APROBADO."""
        return LiquidacionService._sabana(mes, anio, TipoPago.PRONTO_PAGO, filtros)

    @staticmethod
    def _sabana(mes, anio, tipo, filtros=None):
        mes, anio = validar_periodo(mes, anio)

        periodo = (mes, anio)
        filas = LiquidacionService._inscritos(periodo, tipo, filtros)

        if not filas and es_periodo_actual(mes, anio):
            # CR-10 retroceso: el mes en curso aún no se parametriza; se usa
            # la última vigencia de hasta 6 meses atrás (legacy 331–348/411–428).
            for i in range(1, RETROCESO_MAXIMO + 1):
                periodo = restar_meses(mes, anio, i)
                filas = LiquidacionService._inscritos(periodo, tipo, filtros)
                if filas:
                    break

        if not filas:
            raise ValueError(
                f"No se encontraron registros para el mes y año {mes:02d}/{anio}."
            )

        totales = LiquidacionService._totales_por_vehiculo(
            [fila["vehiculo"] for fila in filas],
            periodo[0],
            periodo[1],
            ESTADOS_POR_TIPO[tipo],
        )
        dias_totales = 0
        total = CERO
        for fila in filas:
            acumulado = totales.get(fila["vehiculo"]) or {"dias": 0, "total": CERO}
            fila["dias"] = acumulado["dias"]
            fila["total"] = acumulado["total"]
            dias_totales += acumulado["dias"]
            total += acumulado["total"]

        return {
            "mes": mes,
            "anio": anio,
            "mes_aplicado": periodo[0],
            "anio_aplicado": periodo[1],
            "retroactivo": periodo != (mes, anio),
            "filas": filas,
            "totales": {"dias": dias_totales, "total": total},
        }

    @staticmethod
    def _inscritos(periodo, tipo, filtros=None):
        """Vehículos inscritos en la modalidad para el período (upsert del JSON
        legacy datos.pago_mensual[] / pronto_pago[]) → filas planas de sábana.

        Los JOINs son locales (vehiculo y conductor son de la app transporte),
        por eso sí se puede usar select_related aquí.
        """
        mes, anio = periodo
        pagos = (
            PagoVehiculoMensual.objects.filter(mes=mes, anio=anio, tipo=tipo)
            .select_related("vehiculo", "vehiculo__conductor_habitual")
            .order_by("vehiculo__placa")
        )

        filtros = filtros or {}
        if filtros.get("vehiculo"):
            pagos = pagos.filter(
                vehiculo_id=entero(filtros["vehiculo"], "vehiculo")
            )
        if filtros.get("placa"):
            pagos = pagos.filter(vehiculo__placa__icontains=filtros["placa"])
        if filtros.get("conductor"):
            pagos = pagos.filter(
                vehiculo__conductor_habitual__cedula=str(filtros["conductor"])
            )

        return [
            {
                "vehiculo": pago.vehiculo_id,
                "placa": pago.vehiculo.placa,
                "tipo_contrato": pago.vehiculo.tipo_contrato,
                "conductor_cedula": (
                    pago.vehiculo.conductor_habitual.cedula
                    if pago.vehiculo.conductor_habitual_id
                    else None
                ),
                "valor_dia": pago.vehiculo.valor_dia_base,
                "pagado": pago.pagado,
                "fecha_pago": pago.fecha_pago,
                "total_liquidado": pago.total_liquidado,
            }
            for pago in pagos
        ]

    @staticmethod
    def _totales_por_vehiculo(vehiculo_ids, mes, anio, estados):
        """Σ total_a_pagar y días trabajados por vehículo en el período.

        Una sola query + prefetch de novedades (la propiedad §5.1 resuelve
        valor_dia ± novedad sin N+1).
        """
        vehiculo_ids = list(vehiculo_ids)
        if not vehiculo_ids:
            return {}

        desde, hasta = rango_mes(mes, anio)
        salidas = (
            Salida.objects.filter(
                vehiculo_id__in=vehiculo_ids,
                fecha_salida__gte=desde,
                fecha_salida__lt=hasta,
                estado__in=estados,
            )
            .order_by("fecha_salida")
            .prefetch_related("novedad")
        )

        totales = {}
        for salida in salidas:
            acumulado = totales.setdefault(
                salida.vehiculo_id, {"dias": 0, "total": CERO}
            )
            acumulado["dias"] += 1
            acumulado["total"] += salida.total_a_pagar
        return totales

    # ------------------------------------------------------------------ #
    # Consecutivos atómicos (D3)
    # ------------------------------------------------------------------ #
    @staticmethod
    def proximo_consecutivo(vehiculo_id, mes, anio, actor=None):
        """Réplica de obtenerConsecutivoYRegistrar (legacy 234–289).

        Devuelve (consecutivo, creado):
        - Si el vehículo ya tiene número para el período, se devuelve tal cual
          (idempotente, como el SELECT previo del legacy).
        - Si no, siguiente = MAX(global) + 1 con arranque en 1000 (el legacy
          tomaba el MAX de TODA la tabla, no por vehículo).

        select_for_update() (§5.2) bloquea la lectura en MySQL y erradica la
        carrera MAX+1; en SQLite (tests) es no-op. El unique
        (vehiculo, mes, anio) + IntegrityError cierra la última brecha.
        """
        vehiculo_id = entero(vehiculo_id, "vehiculo")
        mes, anio = validar_periodo(mes, anio)
        if not Vehiculo.objects.filter(pk=vehiculo_id).exists():
            raise ValueError(f"No existe un vehículo con id {vehiculo_id}.")

        with transaction.atomic():
            existente = (
                ConsecutivoMensual.objects.select_for_update()
                .filter(vehiculo_id=vehiculo_id, mes=mes, anio=anio)
                .first()
            )
            if existente:
                return existente, False

            maximo = (
                ConsecutivoMensual.objects.select_for_update()
                .order_by("-consecutivo")
                .values_list("consecutivo", flat=True)
                .first()
            )
            siguiente = maximo + 1 if maximo is not None else CONSECUTIVO_INICIAL
            try:
                # Savepoint: si otra transacción ganó la carrera, el unique
                # revienta aquí sin envenenar la transacción externa.
                with transaction.atomic():
                    consecutivo = ConsecutivoMensual.objects.create(
                        vehiculo_id=vehiculo_id,
                        mes=mes,
                        anio=anio,
                        consecutivo=siguiente,
                        creado_por=actor,
                    )
            except IntegrityError:
                consecutivo = ConsecutivoMensual.objects.get(
                    vehiculo_id=vehiculo_id, mes=mes, anio=anio
                )
                return consecutivo, False
            return consecutivo, True

    # ------------------------------------------------------------------ #
    # Inscripción / marca de pago (D4)
    # ------------------------------------------------------------------ #
    @staticmethod
    def guardar_pago(datos, actor=None):
        """Upsert de la inscripción y marca de pago de un vehículo en un
        período (desempaquetado de los JSON legacy pago_mensual[]/pronto_pago[]).

        Si se marca `pagado` sin total explícito, el snapshot
        `total_liquidado` se calcula con la misma fórmula de la sábana (§5.1).
        """
        vehiculo_id = LiquidacionService._validar_vehiculo(datos.get("vehiculo"))
        mes, anio = validar_periodo(datos.get("mes"), datos.get("anio"))
        tipo = datos.get("tipo")
        if tipo not in TipoPago.values:
            raise ValueError(f"El tipo de pago '{tipo}' no es un valor válido.")

        pagado = bool(datos.get("pagado", False))
        fecha_pago = datos.get("fecha_pago")
        total = datos.get("total_liquidado")
        if pagado and total is None:
            totales = LiquidacionService._totales_por_vehiculo(
                [vehiculo_id], mes, anio, ESTADOS_POR_TIPO[tipo]
            )
            total = (totales.get(vehiculo_id) or {"total": CERO})["total"]
        if total is None:
            total = CERO

        # Transacción externa + savepoint interno: si otra transacción creó la
        # inscripción, el unique revienta solo el savepoint y seguimos con update.
        with transaction.atomic():
            try:
                with transaction.atomic():
                    pago = PagoVehiculoMensual.objects.create(
                        vehiculo_id=vehiculo_id,
                        mes=mes,
                        anio=anio,
                        tipo=tipo,
                        pagado=pagado,
                        fecha_pago=fecha_pago,
                        total_liquidado=total,
                        creado_por=actor,
                    )
            except IntegrityError:
                # Ya inscrito → actualiza la marca (upsert).
                pago = PagoVehiculoMensual.objects.get(
                    vehiculo_id=vehiculo_id, mes=mes, anio=anio, tipo=tipo
                )
                pago.pagado = pagado
                pago.fecha_pago = fecha_pago
                pago.total_liquidado = total
                pago.modificado_por = actor
                pago.save()
        return pago

    # ------------------------------------------------------------------ #
    # Gate de edición tras cierre (B3 / §5.9)
    # ------------------------------------------------------------------ #
    @staticmethod
    def puede_editar_periodo(mes, anio, tiene_permiso_editar=False):
        """False si el período ya pasó su fecha límite y el usuario no tiene
        `transporte.editar_tras_cierre`. Período sin cierre = siempre abierto.
        """
        if tiene_permiso_editar:
            return True
        mes, anio = validar_periodo(mes, anio)
        cierre = FechaLimiteCierre.objects.filter(mes=mes, anio=anio).first()
        if cierre is None:
            return True
        return date.today() <= cierre.fecha_limite

    # ------------------------------------------------------------------ #
    # Validaciones internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_vehiculo(vehiculo):
        """Acepta instancia Vehiculo o pk; exige existencia."""
        if isinstance(vehiculo, Vehiculo):
            return vehiculo.pk
        if vehiculo in (None, ""):
            raise ValueError("El vehículo es obligatorio.")
        vehiculo_id = entero(vehiculo, "vehiculo")
        if not Vehiculo.objects.filter(pk=vehiculo_id).exists():
            raise ValueError(f"No existe un vehículo con id {vehiculo_id}.")
        return vehiculo_id
