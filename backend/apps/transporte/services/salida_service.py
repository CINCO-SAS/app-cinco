"""
SalidaService — núcleo transaccional de salidas (matriz S6/B1–B15, §5.1).

Reglas verificadas en el legacy:

- **CR-9 ventana −2 días hábiles** (`transporte_salida.php` 29–70
  `esDiaValidable` / `base_salida_transporte.php` 49–96
  `restarDiasHabilesTransporte`): ventana ``[hoy − 2 días hábiles, hoy]``
  con sábados NO hábiles (paridad: ver docstring de ``calendario``).
  Para **reportar**: bypass solo por programación/admin (§5.1). Para
  **novedades y eliminación**: estricta salvo jefe validador del área de
  la salida o programación/admin (`base_salida_transporte.php` 754–773 y
  874–891; mensajes legacy literales).
- **CR-1** duplicado (vehículo, fecha) con ``estado != ELIMINADO``
  (`transporte_salida.php` 447–458). **CR-2** duplicado
  (conductor/móvil, fecha) con ``estado != ELIMINADO`` (482–496).
- **Personal estricto** (461–477): si NO es "disponible", quien sale debe
  tener área Y carpeta en ``cinco_base_de_personal``; si es
  "disponible", el área se selecciona manualmente (435–439).
- **Snapshots inmutables**: ``area``/``carpeta``/``sede`` y ``valor_dia``
  se copian a la fila al registrar (§5.1: los cálculos de pago usan el
  snapshot, no la tarifa vigente).
- **Máquina de estados D-A11**: ``REPORTADO → APROBADO/RECHAZADO/
  ELIMINADO`` y ``APROBADO → VALIDADO``; ``RECHAZADO`` es terminal salvo
  borrado lógico (§5.1 `rechazar`). Cada cambio deja
  ``SalidaHistorial`` (fila, no JSON — §7.2) + ``AuditoriaLog``.
- Resolución de cédulas en dos pasos sin JOINs cross-DB (D-A10):
  ``username → Empleado`` (audit) y ``movil_sale → Empleado/Conductor``.

Novedades (B4, §5.1 — legacy `base_salida_transporte.php` `id_row`):

- **UNA por salida** (OneToOne): el legacy sobrescribía
  ``datos.novedad``; aquí ``update_or_create`` con AuditoriaLog
  CREADO/ACTUALIZADO. Solo sobre salidas ``REPORTADO``/``APROBADO``
  (``esGestionable``, líneas 1032–1034) y con la **ventana CR-9** de
  novedades (mensaje literal 768). El total se calcula en servidor
  (``calcular_pago`` = ``valor_dia ± novedad``).
- **Eliminar novedad** (B7): ventana CR-9 o jefe/programación, como en
  legacy (``esValido`` = ventana, línea 2134); solo bloquea estado
  ``ELIMINADO``. Auditoría de borrado.
- **Permisos por fila** (B15): ``perfil_gestion`` resuelve UNA vez por
  request quién es jefe de qué área/carpeta (A1) para evaluar cada fila
  sin N+1.

Papeles (§5.9, hasta E3):
- programación/admin: ``is_staff``/``is_superuser``, grupo
  ``transporte_admin`` o permiso ``transporte.puede_programar`` (el
  permiso/grupos se declaran en E3; hoy ``has_perm`` devuelve False y el
  equivalente operativo es staff).
- jefe validador del área: ``JefeValidador`` vía
  ``ParametrosService.es_jefe_validador`` (A1).
"""
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.empleados.models import Empleado

from ..models import (
    AuditoriaLog,
    Conductor,
    EstadoSalida,
    JefeValidador,
    Novedad,
    Salida,
    SalidaHistorial,
    TipoNovedad,
    Vehiculo,
)
from . import calendario
from .parametros_service import ParametrosService
from .permiso_service import PermisoService

# Sentinellas legacy de `movil_sale` (transporte_salida.php 432, ETL A3).
_DISPONIBLES = ("disponible", "0", "")

# Máquina de estados (D-A11 / §5.1). RECHAZADO es terminal para flujos
# (solo borrado lógico lo remueve); ELIMINADO es estado final.
#
# El legado NO tiene matriz de transiciones: su único guard es
# `WHERE id = ? AND estado != 'eliminado'` (`base_salida_transporte.php`
# 973 y 1159), es decir admite cualquier salto salvo desde ELIMINADO.
# Aquí se endurece a propósito (no se resucita un ELIMINADO ni se
# reabre un RECHAZADO) conservando los dos saltos que el sistema real
# usa, ambos con evidencia en el legado:
#   · APROBADO → RECHAZADO: `rechazar` (base_salida_transporte.php 1159).
#     El rechazo puede caer sobre una salida ya aprobada (documento
#     vencido, error de carga); el guard solo excluye ELIMINADO.
#   · REPORTADO → VALIDADO: WFM masivo
#     (`transporte_validacion_wfm_service.php` 426–445) que valida por
#     lote con observación literal 'validado por sistema'. Es un segundo
#     camino paralelo a VALIDADO que no pasa por APROBADO.
TRANSICIONES = {
    EstadoSalida.REPORTADO: {
        EstadoSalida.APROBADO,
        EstadoSalida.RECHAZADO,
        EstadoSalida.VALIDADO,  # WFM masivo (legacy 427)
        EstadoSalida.ELIMINADO,
    },
    EstadoSalida.APROBADO: {
        EstadoSalida.VALIDADO,
        EstadoSalida.RECHAZADO,  # legacy 1159: solo excluye ELIMINADO
        EstadoSalida.ELIMINADO,
    },
    EstadoSalida.RECHAZADO: {EstadoSalida.ELIMINADO},
    EstadoSalida.VALIDADO: {EstadoSalida.ELIMINADO},
    EstadoSalida.ELIMINADO: set(),
}

# Mensajes legacy literales (transporte_salida.php / base_salida_transporte.php).
MSG_FUERA_VENTANA_REPORTE = "No es posible registrar la salida en esta fecha."
MSG_DISPONIBLE_SIN_AREA = (
    "Debe seleccionar un área para marcar el vehículo como DISPONIBLE."
)
MSG_PERSONAL_SIN_AREA = (
    "La MOVIL {movil} no tiene asignada un área o carpeta asignada, "
    "por favor verifique."
)
MSG_DUPLICADO_VEHICULO = (
    "Ya existe un registro de salida para este vehículo en la fecha seleccionada"
)
MSG_DUPLICADO_MOVIL = (
    "Ya existe un registro de salida para esta móvil en la fecha seleccionada"
)
MSG_FUERA_VENTANA_ELIMINAR = (
    "Solo se permite eliminar registros de hasta máximo 2 días atrás."
)
MSG_FUERA_VENTANA_NOVEDAD = (
    "Solo se permite gestionar novedades de hasta máximo 2 días atrás."
)
MSG_SIN_PERMISO = "No tiene permiso para gestionar esta salida."
MSG_MOTIVO_RECHAZO = "Debe indicar un motivo de rechazo."
# Literal del historial del WFM masivo (transporte_validacion_wfm_service.php 438).
MOTIVO_VALIDADO_WFM = "validado por sistema"
MSG_NOVEDAD_VACIA = "Debe indicar el tipo, el valor y la descripción de la novedad."
MSG_NOVEDAD_VALOR = "El valor de la novedad no puede ser negativo."
MSG_SIN_NOVEDAD = "La salida no tiene novedades registradas."
MSG_NOVEDAD_ESTADO = (
    "Solo se puede reportar novedad sobre salidas en estado REPORTADO "
    "o APROBADO."
)


def _a_fecha(valor):
    """date | datetime | str ISO ('YYYY-MM-DD' o datetime '...T...') → date."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor).strip()[:10])


class PerfilGestion:
    """
    Permisos por fila (B15, §6): "jefe área/carpeta o programación".
    Se resuelve una vez por request (`SalidaService.perfil_gestion`) y
    el serializer pregunta por fila sin volver a tocar BD (sin N+1).
    Réplica de isUserLeaderOfSalida con la misma semántica de carpetas
    vacías (= todas las del área).
    """

    def __init__(self, programacion, jefaturas):
        self.programacion = programacion
        self.jefaturas = jefaturas  # área → set | None (todas)

    def puede_gestionar(self, area, carpeta=None):
        if self.programacion:
            return True
        area = (area or "").strip()
        if area not in self.jefaturas:
            return False
        carpetas = self.jefaturas.get(area)
        if carpetas is None:  # None = todas las carpetas del área
            return True
        return carpeta in carpetas


class SalidaService:
    """Única capa de reglas de negocio de las salidas."""

    # ------------------------------------------------------------------ #
    # CR-9 — ventana contextual (§5.1)
    # ------------------------------------------------------------------ #
    @staticmethod
    def ventana_validacion(fecha, usuario, accion="reportar", area=None,
                           carpeta=None):
        """
        True si `usuario` puede trabajar con una salida de `fecha` bajo CR-9.

        - `accion="reportar"`: ventana [hoy−2 días hábiles, hoy] con
          sábados NO hábiles (legacy `esDiaValidable`); bypass solo con
          programación/admin (§5.1).
        - `accion="novedad"`/`"eliminar"`: misma ventana estricta para el
          operador; jefe validador del `area`/`carpeta` de la salida y
          programación/admin tienen bypass (`base_salida_transporte.php`
          754–773, 874–891).

        Sin bypass, un usuario fuera de ventana NUNCA pasa (fechas
        futuras incluidas). Puro: no escribe BD.
        """
        fecha = _a_fecha(fecha)
        hoy = timezone.localdate()
        limite = calendario.restar_dias_habiles(hoy, 2, sabado_habil=False)
        dentro = limite <= fecha <= hoy

        if SalidaService._puede_programar(usuario):
            return True
        if accion in ("novedad", "eliminar"):
            if SalidaService._es_jefe_de(usuario, area, carpeta):
                return True
        return dentro

    @staticmethod
    def _puede_programar(usuario):
        """Programación/admin (§5.9 / E3): delega en PermisoService."""
        return PermisoService.puede_programar(usuario)

    @staticmethod
    def _es_jefe_de(usuario, area, carpeta=None):
        """Jefe validador ACTIVO del área/carpeta de la salida (A1)."""
        if usuario is None:
            return False
        return ParametrosService.es_jefe_validador(
            getattr(usuario, "username", ""), area, carpeta
        )

    @staticmethod
    def _empleado_de(usuario):
        """username (cédula) → Empleado para la auditoría (D-A10, 2 pasos)."""
        if usuario is None:
            return None
        cedula = str(getattr(usuario, "username", "") or "").strip()
        if not cedula:
            return None
        return Empleado.objects.filter(cedula=cedula).first()

    # ------------------------------------------------------------------ #
    # Registro (S6 / B1)
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def registrar_salida(cls, datos, usuario=None):
        """
        Alta de salida (legacy `transporte_salida.php` 380–552).

        `datos`: fecha_salida, vehiculo (instancia o pk), movil_sale
        (cédula del personal que sale o 'disponible'), cc_asignada,
        area/carpeta/sede (manuales, exigidos con 'disponible'),
        observacion y valor_dia (opcional; por defecto la tarifa del
        vehículo).

        Validaciones en orden: ventana CR-9 → reglas de disponible /
        personal → CR-1 → CR-2. Crea la fila en REPORTADO con semilla de
        historial y AuditoriaLog, todo en transacción.
        """
        fecha = _a_fecha(datos["fecha_salida"])
        if not cls.ventana_validacion(fecha, usuario, "reportar"):
            raise ValueError(MSG_FUERA_VENTANA_REPORTE)

        vehiculo = datos["vehiculo"]
        if not isinstance(vehiculo, Vehiculo):
            vehiculo = Vehiculo.objects.get(pk=vehiculo)

        movil_sale = str(datos.get("movil_sale") or "").strip()
        es_disponible = movil_sale.lower() in _DISPONIBLES

        area = str(datos.get("area") or "").strip()
        carpeta = str(datos.get("carpeta") or "").strip()
        sede = str(datos.get("sede") or "").strip()
        conductor = None

        if es_disponible:
            # transporte_salida.php 435–439: el área se elige a mano.
            if not area:
                raise ValueError(MSG_DISPONIBLE_SIN_AREA)
        else:
            # 461–477: quien sale DEBE tener área y carpeta en personal.
            personal = Empleado.objects.filter(
                cedula=movil_sale
            ).first()
            if (
                personal is None
                or not (personal.area or "").strip()
                or not (personal.carpeta or "").strip()
            ):
                raise ValueError(MSG_PERSONAL_SIN_AREA.format(movil=movil_sale))
            # Snapshots desde personal (legacy datos.area_sale/carpeta_sale/
            # sede_sale venían de la misma fila); el payload puede ajustarlos.
            area = area or (personal.area or "").strip()
            carpeta = carpeta or (personal.carpeta or "").strip()
            sede = sede or (personal.sede or "").strip()
            # D-A10 paso 2: si además está en conductores, queda como FK
            # (habilita CR-2); si no, conductor=None como la ETL.
            conductor = Conductor.objects.filter(cedula=movil_sale).first()

        # CR-1 (447–458): vehículo-día contra salidas vivas.
        if Salida.objects.filter(
            vehiculo=vehiculo, fecha_salida=fecha
        ).exclude(estado=EstadoSalida.ELIMINADO).exists():
            raise ValueError(MSG_DUPLICADO_VEHICULO)

        # CR-2 (482–496): móvil-día contra salidas vivas. Aplica cuando
        # "quien sale" tiene registro de Conductor (el legacy comparaba la
        # columna movil_sale sin resolver tipo; ver nota en el ROADMAP C4).
        if conductor and Salida.objects.filter(
            conductor=conductor, fecha_salida=fecha
        ).exclude(estado=EstadoSalida.ELIMINADO).exists():
            raise ValueError(MSG_DUPLICADO_MOVIL)

        tecnico = None
        cc_asignada = str(datos.get("cc_asignada") or "").strip()
        if cc_asignada:
            tecnico = Empleado.objects.filter(cedula=cc_asignada).first()

        valor_dia = datos.get("valor_dia")
        if valor_dia is None:
            valor_dia = vehiculo.valor_dia_base

        empleado = cls._empleado_de(usuario)
        salida = Salida.objects.create(
            vehiculo=vehiculo,
            fecha_salida=fecha,
            conductor=conductor,
            tecnico_asignado=tecnico,
            es_disponible=es_disponible,
            area=area,
            carpeta=carpeta,
            sede=sede,
            valor_dia=valor_dia,
            estado=EstadoSalida.REPORTADO,
            observacion=str(datos.get("observacion") or ""),
            creado_por=empleado,
        )
        # Semilla de historial (base_salida_transporte.php 946–951).
        SalidaHistorial.objects.create(
            salida=salida,
            estado=EstadoSalida.REPORTADO,
            motivo="",
            fecha_cambio=timezone.now(),
            creado_por=empleado,
        )
        cls._auditar(salida, "CREADO", None, {"estado": salida.estado}, empleado)
        return salida

    # ------------------------------------------------------------------ #
    # Pre-chequeo S3 (kiosco) — SOLO LECTURA
    # ------------------------------------------------------------------ #
    @staticmethod
    def pre_validar(fecha, vehiculo, movil_sale="", usuario=None):
        """
        S3 kiosco: pre-chequeo de fecha/vehículo/móvil ANTES del alta S6.

        Legacy `transporte_salida.php`: `validar_fecha` (160–201, devuelve
        ``validable`` = CR-9 y el registro ``APROBADO`` del vehículo ese día)
        y `cedula_movil` (204–219, chequeo de la móvil). Se añaden las
        reglas de bloqueo reales CR-1/CR-2 que aplicará ``registrar_salida``
        para que la UI sepa de antemano si el alta pasará. **No escribe BD.**

        Devuelve ``{validable, duplicado_vehiculo, duplicado_movil,
        puede_registrar, mensaje, registro, salida}`` donde ``mensaje`` es el
        literal legacy del primer bloqueo (o ``None``).
        """
        fecha = _a_fecha(fecha)
        if not isinstance(vehiculo, Vehiculo):
            vehiculo = Vehiculo.objects.get(pk=vehiculo)

        validable = SalidaService.ventana_validacion(fecha, usuario, "reportar")

        # Información legacy: registro APROBADO del vehículo ese día.
        registro = (
            Salida.objects.filter(
                vehiculo=vehiculo, fecha_salida=fecha,
                estado=EstadoSalida.APROBADO,
            )
            .order_by("-id")
            .first()
        )
        # Salida viva (CR-1) del vehículo ese día.
        salida_viva = (
            Salida.objects.filter(vehiculo=vehiculo, fecha_salida=fecha)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .order_by("-id")
            .first()
        )
        duplicado_vehiculo = salida_viva is not None

        # CR-2: la móvil que sale, contra su FK conductor (D-A10). Aplica
        # solo si quien sale no es "disponible" y está en conductores; el
        # alcance exacto de CR-2 se concilia con datos reales en C4.
        duplicado_movil = False
        movil = str(movil_sale or "").strip()
        if movil and movil.lower() not in _DISPONIBLES:
            conductor = Conductor.objects.filter(cedula=movil).first()
            if conductor:
                duplicado_movil = Salida.objects.filter(
                    conductor=conductor, fecha_salida=fecha
                ).exclude(estado=EstadoSalida.ELIMINADO).exists()

        if not validable:
            mensaje = MSG_FUERA_VENTANA_REPORTE
        elif duplicado_vehiculo:
            mensaje = MSG_DUPLICADO_VEHICULO
        elif duplicado_movil:
            mensaje = MSG_DUPLICADO_MOVIL
        else:
            mensaje = None

        return {
            "validable": validable,
            "duplicado_vehiculo": duplicado_vehiculo,
            "duplicado_movil": duplicado_movil,
            "puede_registrar": mensaje is None,
            "mensaje": mensaje,
            "registro": registro,
            "salida": salida_viva,
        }

    # ------------------------------------------------------------------ #
    # Consulta (B1)
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar(query_params):
        """
        Filtros server-side (§6 B1): desde/hasta (rango de fechas),
        estado, vehiculo (pk o placa), conductor (pk), area, search
        (placa/cédula/nombre/observación/área).

        Por defecto excluye ELIMINADO; con `?estado=` se muestra ese
        estado explícitamente (incluido ELIMINADO).
        """
        queryset = Salida.objects.select_related(
            "vehiculo", "conductor", "tecnico_asignado", "novedad"
        )

        desde = (query_params.get("desde") or "").strip()
        if desde:
            queryset = queryset.filter(fecha_salida__gte=_a_fecha(desde))
        hasta = (query_params.get("hasta") or "").strip()
        if hasta:
            queryset = queryset.filter(fecha_salida__lte=_a_fecha(hasta))

        estado = (query_params.get("estado") or "").strip().upper()
        if estado:
            queryset = queryset.filter(estado=estado)
        else:
            queryset = queryset.exclude(estado=EstadoSalida.ELIMINADO)

        vehiculo = (query_params.get("vehiculo") or "").strip()
        if vehiculo:
            if vehiculo.isdigit():
                queryset = queryset.filter(vehiculo_id=int(vehiculo))
            else:
                queryset = queryset.filter(vehiculo__placa__iexact=vehiculo)

        conductor = (query_params.get("conductor") or "").strip()
        if conductor:
            queryset = queryset.filter(conductor_id=int(conductor))

        area = (query_params.get("area") or "").strip()
        if area:
            queryset = queryset.filter(area__iexact=area)

        search = (query_params.get("search") or "").strip()
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(vehiculo__placa__icontains=search)
                | Q(conductor__cedula__icontains=search)
                | Q(conductor__nombre_completo__icontains=search)
                | Q(area__icontains=search)
                | Q(observacion__icontains=search)
            )

        return queryset.order_by("-fecha_salida", "-id")

    @staticmethod
    def obtener(salida_id):
        """Salida con relaciones; ValueError si no existe."""
        salida = Salida.objects.select_related(
            "vehiculo", "conductor", "tecnico_asignado"
        ).filter(pk=salida_id).first()
        if salida is None:
            raise ValueError("No existe la salida %s." % salida_id)
        return salida

    # ------------------------------------------------------------------ #
    # Máquina de estados (D-A11)
    # ------------------------------------------------------------------ #
    @classmethod
    def aprobar(cls, salida_id, usuario=None):
        """REPORTADO → APROBADO (jefe del área o programación, §5.1)."""
        salida = cls.obtener(salida_id)
        return cls._cambiar_estado(salida, EstadoSalida.APROBADO, usuario)

    @classmethod
    @transaction.atomic
    def aprobar_masivo(cls, ids, usuario=None):
        """Aprueba `ids` en una sola transacción con historial por fila
        (§5.1 `aprobar_masivo`): o todas o ninguna."""
        ids = list(dict.fromkeys(ids))
        if not ids:
            raise ValueError("Debe indicar al menos una salida.")
        salidas = Salida.objects.select_for_update().filter(pk__in=ids)
        if len(salidas) != len(ids):
            raise ValueError("Algunas de las salidas indicadas no existen.")
        return [
            cls._cambiar_estado(s, EstadoSalida.APROBADO, usuario)
            for s in salidas
        ]

    @classmethod
    def rechazar(cls, salida_id, motivo, usuario=None):
        """RECHAZADO con motivo obligatorio (B13 / §5.1)."""
        motivo = str(motivo or "").strip()
        if not motivo:
            raise ValueError(MSG_MOTIVO_RECHAZO)
        salida = cls.obtener(salida_id)
        return cls._cambiar_estado(
            salida, EstadoSalida.RECHAZADO, usuario, motivo=motivo
        )

    @classmethod
    def validar(cls, salida_id, usuario=None):
        """APROBADO → VALIDADO (D-A11)."""
        salida = cls.obtener(salida_id)
        return cls._cambiar_estado(salida, EstadoSalida.VALIDADO, usuario)

    @classmethod
    def validar_wfm(cls, salidas, edit_cedula=""):
        """
        Validación WFM masiva (F5-5): `reportado → validado` en bloque.

        Es el equivalente a `transporteWfmApplyValidationChunk`
        (transporte_validacion_wfm_service.php 426–445), que hace un único
        UPDATE **sin chequear permisos** porque es un proceso autónomo y no
        una acción de un jefe. Aquí se mantiene ese gate abierto
        (``requiere_gestion=False``) pero la autorización vive en el
        endpoint WFM, y la máquina de estados D-A11 sigue aplicando.

        Observación literal del legado: 'validado por sistema'. La
        auditoría se atribuye a la cédula ``edit_cedula`` si hay Empleado
        correspondiente (el legado guardaba la cédula cruda en `edit`).
        """
        cedula = str(edit_cedula or "").strip()
        empleado = (
            Empleado.objects.filter(cedula=cedula).first() if cedula else None
        )
        return [
            cls._cambiar_estado(
                salida,
                EstadoSalida.VALIDADO,
                None,
                motivo=MOTIVO_VALIDADO_WFM,
                requiere_gestion=False,
                empleado=empleado,
            )
            for salida in salidas
        ]

    @classmethod
    def eliminar(cls, salida_id, usuario=None):
        """Borrado lógico (B5): CR-9 estricto para el operador con el
        mensaje legacy (`base_salida_transporte.php` 882–887) y libera
        CR-1 para otro despacho el mismo día."""
        salida = cls.obtener(salida_id)
        if not cls.ventana_validacion(
            salida.fecha_salida, usuario, "eliminar",
            area=salida.area, carpeta=salida.carpeta,
        ):
            raise ValueError(MSG_FUERA_VENTANA_ELIMINAR)
        # La autorización ya la resolvió la ventana (jefe/programación
        # bypass; operador dentro de ventana). No se exige gestión aquí.
        return cls._cambiar_estado(
            salida, EstadoSalida.ELIMINADO, usuario, requiere_gestion=False
        )

    # ------------------------------------------------------------------ #
    # Novedades (B6/B7, §5.1)
    # ------------------------------------------------------------------ #
    @classmethod
    def registrar_novedad(cls, salida_id, tipo, valor, descripcion,
                          usuario=None):
        """
        Reporta la novedad de la salida (B6, `id_row` de
        `base_salida_transporte.php` 723–833).

        UNA por salida: el legacy sobrescribía ``datos.novedad``; aquí se
        conserva el comportamiento con update sobre la fila única
        (§3.C). Ventana CR-9 para novedades (línea 763–771) y estados
        ``REPORTADO``/``APROBADO`` (``esGestionable``, 1032–1034).
        Devuelve la ``Novedad``.
        """
        salida = cls.obtener(salida_id)
        if not cls.ventana_validacion(
            salida.fecha_salida, usuario, "novedad",
            area=salida.area, carpeta=salida.carpeta,
        ):
            raise ValueError(MSG_FUERA_VENTANA_NOVEDAD)
        if salida.estado not in (
            EstadoSalida.REPORTADO, EstadoSalida.APROBADO
        ):
            raise ValueError(MSG_NOVEDAD_ESTADO)

        tipo = str(tipo or "").strip().upper()
        descripcion = str(descripcion or "").strip()
        if tipo not in TipoNovedad.values or not descripcion:
            raise ValueError(MSG_NOVEDAD_VACIA)
        try:
            valor = Decimal(str(valor))
        except Exception:
            raise ValueError(MSG_NOVEDAD_VACIA)
        if valor < 0:
            raise ValueError(MSG_NOVEDAD_VALOR)

        empleado = cls._empleado_de(usuario)
        # UNA por salida (OneToOne): sobrescribe como el legacy.
        novedad, creada = Novedad.objects.update_or_create(
            salida=salida,
            defaults={
                "tipo": tipo,
                "valor": valor,
                "descripcion": descripcion,
                "creado_por": empleado,
                "modificado_por": empleado,
            },
        )
        cls._auditar(
            salida,
            "NOVEDAD_CREADA" if creada else "NOVEDAD_ACTUALIZADA",
            None,
            {
                "tipo": tipo,
                "valor": str(valor),
                "descripcion": descripcion,
            },
            empleado,
        )
        return novedad

    @classmethod
    def eliminar_novedad(cls, salida_id, usuario=None):
        """
        Limpia la novedad con auditoría (B7, legacy `eliminar_novedad`
        que vaciaba `datos.novedad`). Ventana CR-9 como al reportar
        (CR-9 aplica a novedades); solo bloquea salidas ELIMINADO.
        """
        salida = cls.obtener(salida_id)
        if salida.estado == EstadoSalida.ELIMINADO:
            raise ValueError(MSG_NOVEDAD_ESTADO)
        if not cls.ventana_validacion(
            salida.fecha_salida, usuario, "novedad",
            area=salida.area, carpeta=salida.carpeta,
        ):
            raise ValueError(MSG_FUERA_VENTANA_NOVEDAD)
        try:
            novedad = salida.novedad
        except Novedad.DoesNotExist:
            raise ValueError(MSG_SIN_NOVEDAD)

        empleado = cls._empleado_de(usuario)
        datos_antes = {
            "tipo": novedad.tipo,
            "valor": str(novedad.valor),
            "descripcion": novedad.descripcion,
        }
        novedad.delete()
        cls._auditar(
            salida, "NOVEDAD_ELIMINADA", datos_antes, None, empleado
        )
        return True

    @staticmethod
    def calcular_pago(salida):
        """
        ``valor_dia ± novedad`` (§5.1) — implementación única
        determinista: delega en la propiedad del modelo.
        """
        return salida.total_a_pagar

    @staticmethod
    def historial(salida_id):
        """Filas de ``SalidaHistorial`` de la salida (§7.2), más
        recientes primero; error si la salida no existe."""
        SalidaService.obtener(salida_id)  # valida existencia
        return SalidaHistorial.objects.filter(salida_id=salida_id).order_by(
            "-fecha_cambio", "-id"
        )

    # ------------------------------------------------------------------ #
    # Permisos por fila (B15, §6)
    # ------------------------------------------------------------------ #
    @classmethod
    def perfil_gestion(cls, usuario):
        """
        Perfil del usuario para evaluar permisos POR FILA (B15) sin N+1:
        se resuelve UNA vez por request (programación o jefaturas de
        área/carpeta desde A1) y el serializer consulta por fila.
        """
        if usuario is None:
            return PerfilGestion(False, {})
        if cls._puede_programar(usuario):
            return PerfilGestion(True, {})
        cedula = str(getattr(usuario, "username", "") or "").strip()
        try:
            empleado_id = Empleado.objects.values_list(
                "id", flat=True
            ).get(cedula=cedula)
        except Empleado.DoesNotExist:
            return PerfilGestion(False, {})
        jefaturas = {}  # área → set de carpetas, o None = todas
        for jefe in JefeValidador.objects.filter(
            empleado_id=empleado_id, activo=True
        ):
            carpetas_area = jefe.carpetas_por_area or {}
            for area in jefe.areas or []:
                carpetas = carpetas_area.get(area) or []
                # Lista vacía = todas las carpetas del área (A1).
                cubiertas = None if not carpetas else set(carpetas)
                if area not in jefaturas:
                    jefaturas[area] = cubiertas
                elif jefaturas[area] is None or cubiertas is None:
                    jefaturas[area] = None
                else:
                    jefaturas[area] = jefaturas[area] | cubiertas
        return PerfilGestion(False, jefaturas)

    @classmethod
    def _cambiar_estado(cls, salida, destino, usuario, motivo="",
                        requiere_gestion=True, empleado=None):
        permitidos = TRANSICIONES.get(salida.estado, set())
        if destino not in permitidos:
            raise ValueError(
                "Transición no permitida: %s → %s." % (salida.estado, destino)
            )
        if requiere_gestion:
            if not cls._puede_programar(usuario) and not cls._es_jefe_de(
                usuario, salida.area, salida.carpeta
            ):
                raise ValueError(MSG_SIN_PERMISO)

        if empleado is None:
            empleado = cls._empleado_de(usuario)
        estado_previo = salida.estado
        salida.estado = destino
        salida.modificado_por = empleado
        salida.save(update_fields=["estado", "modificado_por", "modificado_en"])
        # Historial por fila (§7.2: filas, no JSON).
        SalidaHistorial.objects.create(
            salida=salida,
            estado=destino,
            motivo=motivo,
            fecha_cambio=timezone.now(),
            creado_por=empleado,
        )
        cls._auditar(
            salida,
            "CAMBIO_ESTADO",
            {"estado": estado_previo},
            {"estado": destino, "motivo": motivo},
            empleado,
        )
        return salida

    @staticmethod
    def _auditar(salida, accion, antes, despues, empleado):
        AuditoriaLog.objects.create(
            tabla="transporte_salida",
            accion=accion,
            registro_id=salida.pk,
            datos_antes=antes,
            datos_despues=despues,
            creado_por=empleado,
        )
