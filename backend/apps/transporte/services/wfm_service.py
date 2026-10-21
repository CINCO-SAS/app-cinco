"""
WfmService — F5-5 · validación WFM masiva (§5.10).

Port de `transporte_validacion_wfm_service.php` (836 L) y de las tres
acciones del controlador (`controlador_transporte_salida_informe.php`
128–214): ``validarWFM`` (lote síncrono), ``crearJobValidarWFM`` (cola)
y ``estadoJobValidarWFM`` (estado + respaldo síncrono).

QUÉ HACE EL WFM
---------------
Valida en bloque salidas que quedaron ``REPORTADO``, sustentando que la
persona sí trabajó ese día. La evidencia se busca en dos tablas ajenas
(**solo lectura**, BD ``azul``):

1. ``residencial_base_wfm`` — fuente primaria: la cédula
   (``external_id`` o ``cc_auxiliar``) tuvo actividad ese día.
2. ``logistica_actividades_modulo_agenda`` — respaldo, SOLO si esa
   persona no tiene **ningún** registro WFM ese día (por ``cedula`` o
   ``movil``, en ``fecha`` o ``fecha_cierre``).

Ventana: hoy y hasta 2 días hábiles atrás (sábado y domingo no cuentan,
igual que el legacy), rango semiabierto ``[desde, hasta)``.

HALLAZGO — distinción vestigial en el legado
--------------------------------------------
``transporteWfmFindIdsToValidate`` construye DOS mapas,
``$wfmCompletadoMap`` y ``$wfmAnyMap``, y luego usa el segundo para
decidir si cae al respaldo de agenda. Pero ambos se pueblan con el MISMO
``foreach`` sobre la misma consulta (líneas 294–301), sin ningún filtro
de estado: son siempre idénticos. La intención original (¿"completado"
vs "cualquier actividad"?) se perdió; aquí la regla se implementa en su
forma efectiva y documentada:

    si hay registro WFM ese día  → válido
    si no hay NINGUNO           → válido si aparece en la agenda
    si hay registro WFM "parcial" → en la práctica no existe tal caso
                                   (los mapas son el mismo), así que no
                                   se reproduce una exclusión que el
                                   sistema real no aplica.

MEJORAS SOBRE EL LEGADO
-----------------------
- El lote se aplica dentro de ``transaction.atomic`` con
  ``select_for_update``: el legado hacía un ``UPDATE`` a ciegas por
  ``id IN (...)`` sin bloquear filas, lo que permitía que un jefe
  aprobara la misma salida entre la selección y el UPDATE (y el UPDATE
  la dejaba ``validado`` sin pasar por ``aprobado``, perdiendo el estado).
  Aquí la fila se relee bloqueada y la máquina de estados D-A11 decide.
- ``_contar_reportados`` y ``_elegibles`` se acotan a la misma ventana
  en servidor; el legado confiaba en los parámetros del POST.
"""
from datetime import date, datetime, time, timedelta
import uuid

from django.db import transaction
from django.db.models import Case, IntegerField, Q, When
from django.utils import timezone

from apps.empleados.models import Empleado

from ..models import (
    AgendaLogistica,
    EstadoSalida,
    EstadoWfmJob,
    ResidencialWfm,
    Salida,
    WfmJob,
)
from .calendario import restar_dias_habiles
from .salida_service import SalidaService, _a_fecha

# Tamaño del trozo con el que se consultan tablas ajenas (evita IN() gigantes).
_TROZO_IDENTIDADES = 500


def _mes_valido(mes, yyyy):
    """¿(mes, yyyy) es una fecha de calendario real? (PHP checkdate)"""
    try:
        date(int(yyyy), int(mes), 1)
    except (TypeError, ValueError):
        return False
    return True


def _siguiente_mes(fecha):
    """Primer día del mes siguiente."""
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 1)
    return date(fecha.year, fecha.month + 1, 1)


def _trocear(valores, tamano):
    """Divide una lista en trozos de a `tamano`."""
    valores = list(valores)
    for inicio in range(0, len(valores), tamano):
        yield valores[inicio:inicio + tamano]


class WfmService:
    """Validación WFM masiva (cola + lote + elegibilidad)."""

    # La validación aplica a hoy y hasta 2 días hábiles atrás (legacy 43).
    DIAS_HABILES_ATRAS = 2

    # Límites del lote (legacy 116–117): 1..100 filas por pasada y al
    # menos 500 candidatos para no dejar salidas atrás por el recorte.
    LOTE_DEFECTO = 25
    LOTE_MAXIMO = 100
    CANDIDATOS_POR_LOTE = 10
    CANDIDATOS_MINIMOS = 500

    # Límite del chunk de un job (legacy ProcessJob: chunkDays=1, batch=15).
    DIAS_POR_CHUNK = 1
    LOTE_POR_CHUNK = 15

    # Detección de jobs colgados (legacy FormatearJobRespuesta 769–772).
    JOB_PENDIENTE_COLGADO_SEG = 90
    JOB_PROCESANDO_COLGADO_SEG = 300
    JOB_STALE_CLAIM_SEG = 15

    # Mensajes legacy literales.
    MSG_RANGO_INVALIDO = (
        "El periodo seleccionado no contiene fechas validables. Solo se "
        "permite validar hoy, 1 y 2 dias habiles atras (72 horas aprox)."
    )
    MSG_RANGO_FECHAS = "Rango de fechas invalido."
    MSG_SIN_REGISTROS = "No se encontraron registros para validar"
    MSG_VALIDADOS = "Registros validados exitosamente"
    MSG_JOB_SIN_UUID = "No se recibio el identificador del job."
    MSG_JOB_NO_ENCONTRADO = "No se encontro el job solicitado."
    MSG_JOB_RANGO = "El job tiene un rango de fechas invalido."
    MSG_JOB_CURSOR = "El job no tiene fecha_cursor valida."
    MSG_JOB_NO_CREADO = "No fue posible crear el job de validacion WFM."
    MSG_COLA_EXISTENTE = "Ya existe un proceso en curso para este periodo y area."
    MSG_COLA_NUEVA = "El proceso fue enviado a la cola de validacion."
    MSG_COLGADO_PENDIENTE = (
        "Sigue pendiente. El worker no ha tomado el job; revisa cron, ruta "
        "del script o permisos de ejecucion."
    )
    MSG_COLGADO_PROCESANDO = (
        "El job sigue procesando pero no reporta avance reciente; revisa "
        "el log del worker."
    )

    # ------------------------------------------------------------------ #
    # Ventana (legacy ResolveRange 24–66)
    # ------------------------------------------------------------------ #
    @classmethod
    def limite_inferior(cls, hoy=None):
        """``hoy − 2 días hábiles``. Sábado y domingo NO cuentan, como el
        legacy (bloquea ``$esSab``, ``$esDom`` y ``$esFest``)."""
        hoy = hoy or timezone.localdate()
        return restar_dias_habiles(
            hoy, cls.DIAS_HABILES_ATRAS, sabado_habil=False
        )

    @classmethod
    def limite_superior(cls, hoy=None):
        """``mañana`` (semiabierto): incluye TODO el día de hoy."""
        return (hoy or timezone.localdate()) + timedelta(days=1)

    @classmethod
    def acotar(cls, desde, hasta, hoy=None):
        """Recorta un rango a la ventana permitida (legacy 75–83)."""
        hoy = hoy or timezone.localdate()
        return (
            max(_a_fecha(desde), cls.limite_inferior(hoy)),
            min(_a_fecha(hasta), cls.limite_superior(hoy)),
        )

    @classmethod
    def resolver_rango(cls, mes=None, yyyy=None, fecha_inicio=None,
                       fecha_fin=None, hoy=None):
        """
        (desde, hasta) semiabierto y acotado a la ventana.

        Entradas posibles (legacy 31–55):
        - ``fecha_inicio`` + ``fecha_fin`` (INCLUSIVAS, como el POST del
          legado): se convierten a semiabiertas y se acotan.
        - ``mes`` + ``yyyy``: solo valida que el mes tenga fechas
          validables; el rango sigue siendo la ventana (el legado no
          ampliaba la ventana por mes).
        - nada: la ventana completa.
        """
        hoy = hoy or timezone.localdate()
        minimo = cls.limite_inferior(hoy)
        maximo = cls.limite_superior(hoy)

        if fecha_inicio and fecha_fin:
            try:
                desde = _a_fecha(fecha_inicio)
                hasta = _a_fecha(fecha_fin) + timedelta(days=1)
            except (TypeError, ValueError):
                raise ValueError(cls.MSG_RANGO_FECHAS)
            desde, hasta = max(desde, minimo), min(hasta, maximo)
        else:
            if mes not in (None, "") and yyyy and _mes_valido(mes, yyyy):
                inicio_mes = date(int(yyyy), int(mes), 1)
                if _siguiente_mes(inicio_mes) <= minimo or inicio_mes >= maximo:
                    raise ValueError(cls.MSG_RANGO_INVALIDO)
            desde, hasta = minimo, maximo

        if desde >= hasta:
            raise ValueError(cls.MSG_RANGO_INVALIDO)
        return desde, hasta

    # ------------------------------------------------------------------ #
    # Elegibilidad (legacy FindIdsToValidate 108–396)
    # ------------------------------------------------------------------ #
    @classmethod
    def _identidades(cls, salida):
        """
        (cédulas, móviles) de una salida, con el mapeo de la ETL A3:

        - legacy ``cedula_tecnico`` (móvil asignada, personal de nómina)
          → ``tecnico_asignado.cedula``
        - legacy ``movil_sale`` / ``cc_sale`` (quien sale) →
          ``conductor.cedula``
        - legacy ``movil_sale`` como identificador de móvil →
          ``tecnico_asignado.movil``
        """
        cedulas, moviles = set(), set()
        if salida.conductor_id:
            cedulas.add(str(salida.conductor.cedula or "").strip())
        tecnico = salida.tecnico_asignado
        if tecnico is not None:
            cedulas.add(str(tecnico.cedula or "").strip())
            moviles.add(str(getattr(tecnico, "movil", "") or "").strip())
        return {c for c in cedulas if c and c != "0"}, {
            m for m in moviles if m and m != "0"
        }

    @classmethod
    def _mapa_personal(cls, cedulas, moviles):
        """
        ``cinco_base_de_personal`` ACTIVO: mapa móvil↔cédula para cruzar
        identidades (legacy 196–220). Una misma persona puede tener
        varias cédulas/móviles asociados.
        """
        movil_a_cedula, cedula_a_movil = {}, {}
        if not cedulas and not moviles:
            return movil_a_cedula, cedula_a_movil

        # El legacy filtra `estado = 'activo'` (minúscula); el modelo usa
        # mayúsculas (D-A6) y hay legacy en ambos casos → iexact.
        filas = Empleado.objects.filter(estado__iexact="activo").filter(
            Q(cedula__in=cedulas) | Q(movil__in=moviles)
        ).values_list("cedula", "movil")

        for cedula, movil in filas:
            cedula, movil = (cedula or "").strip(), (movil or "").strip()
            if not movil or not cedula:
                continue
            movil_a_cedula.setdefault(movil, set()).add(cedula)
            cedula_a_movil.setdefault(cedula, set()).add(movil)
        return movil_a_cedula, cedula_a_movil

    @classmethod
    def _presencia_wfm(cls, identidades, desde, hasta):
        """
        Conjunto de ``(identidad, fecha)`` con actividad en
        ``residencial_base_wfm`` (solo lectura).

        El legacy compara la columna DATETIME contra cadenas 'Y-m-d', lo
        que en MySQL las convierte a medianoche: aquí se traduce a
        ``[desde 00:00, hasta 00:00)``.
        """
        if not identidades:
            return set()
        inicio = datetime.combine(desde, time.min)
        fin = datetime.combine(hasta, time.min)
        presencia = set()
        for trozo in _trocear(identidades, _TROZO_IDENTIDADES):
            filas = ResidencialWfm.objects.filter(
                Q(external_id__in=trozo) | Q(cc_auxiliar__in=trozo),
                fecha__gte=inicio,
                fecha__lt=fin,
            ).values_list("external_id", "cc_auxiliar", "fecha")
            for external_id, cc_auxiliar, fecha in filas:
                if fecha is None:
                    continue
                dia = fecha.date()
                for identidad in (external_id, cc_auxiliar):
                    identidad = (identidad or "").strip()
                    if identidad:
                        presencia.add((identidad, dia))
        return presencia

    @classmethod
    def _presencia_agenda(cls, cedulas, moviles, desde, hasta_inclusiva):
        """
        Respaldo: ``logistica_actividades_modulo_agenda`` (solo lectura).

        Cualquier coincidencia por ``cedula`` o por ``movil``, ya sea en
        ``fecha`` o en ``fecha_cierre`` (legacy 305–345; el rango ahí es
        INCLUSIVO en ambos extremos).
        """
        presencia = set()
        if cedulas:
            for trozo in _trocear(cedulas, _TROZO_IDENTIDADES):
                filas = AgendaLogistica.objects.filter(
                    Q(fecha__date__gte=desde, fecha__date__lte=hasta_inclusiva)
                    | Q(
                        fecha_cierre__date__gte=desde,
                        fecha_cierre__date__lte=hasta_inclusiva,
                    ),
                    cedula__in=trozo,
                ).values_list("cedula", "movil", "fecha", "fecha_cierre")
                presencia |= cls._a_pares_agenda(filas)
        if moviles:
            for trozo in _trocear(moviles, _TROZO_IDENTIDADES):
                filas = AgendaLogistica.objects.filter(
                    Q(fecha__date__gte=desde, fecha__date__lte=hasta_inclusiva)
                    | Q(
                        fecha_cierre__date__gte=desde,
                        fecha_cierre__date__lte=hasta_inclusiva,
                    ),
                    movil__in=trozo,
                ).values_list("cedula", "movil", "fecha", "fecha_cierre")
                presencia |= cls._a_pares_agenda(filas)
        return presencia

    @staticmethod
    def _a_pares_agenda(filas):
        """(identidad, día) para cada columna identificable de la agenda."""
        pares = set()
        for cedula, movil, fecha, fecha_cierre in filas:
            for identidad in (cedula, movil):
                identidad = (identidad or "").strip()
                if not identidad:
                    continue
                for marca in (fecha, fecha_cierre):
                    if marca is not None:
                        pares.add((identidad, marca.date()))
        return pares

    @classmethod
    def _candidatos(cls, desde, hasta, area, limite):
        """Salidas ``REPORTADO`` de la ventana, día a día (legacy 134–162)."""
        cantidad = max(
            limite * cls.CANDIDATOS_POR_LOTE, cls.CANDIDATOS_MINIMOS
        )
        consulta = Salida.objects.filter(
            estado=EstadoSalida.REPORTADO,
            fecha_salida__gte=desde,
            fecha_salida__lt=hasta,
        )
        area = (area or "").strip()
        if area and area.upper() not in ("TODAS", "TODOS"):
            consulta = consulta.filter(area__iexact=area)
        return list(
            consulta.select_related("conductor")
            # Cross-BD: tecnico_asignado vive en azul (Empleado); un
            # select_related sería un JOIN imposible para Django (1146).
            .prefetch_related("tecnico_asignado")
            .order_by("fecha_salida", "pk")[:cantidad]
        )

    @classmethod
    def _acotar_y_elegir(cls, desde, hasta, area, limite, hoy=None,
                         acotar=True):
        """Ventana acotada + candidatos + sus identidades expandidas."""
        if acotar:
            desde, hasta = cls.acotar(desde, hasta, hoy)
        if desde >= hasta:
            return desde, hasta, [], {}, set(), set()

        salidas = cls._candidatos(desde, hasta, area, limite)
        if not salidas:
            return desde, hasta, [], {}, set(), set()

        por_salida = {}
        todas_cedulas, todas_moviles = set(), set()
        for salida in salidas:
            cedulas, moviles = cls._identidades(salida)
            por_salida[salida.pk] = [cedulas, moviles]
            todas_cedulas |= cedulas
            todas_moviles |= moviles

        # Cruce movil ↔ cedula con el personal activo (legacy 244–257).
        movil_a_cedula, cedula_a_movil = cls._mapa_personal(
            todas_cedulas, todas_moviles
        )
        for cedulas, moviles in por_salida.values():
            expandidas = set(cedulas)
            for movil in moviles:
                expandidas |= movil_a_cedula.get(movil, set())
            expandidos = set(moviles)
            for cedula in cedulas:
                expandidos |= cedula_a_movil.get(cedula, set())
            cedulas.clear()
            moviles.clear()
            cedulas |= expandidas
            moviles |= expandidos
            todas_cedulas |= expandidas
            todas_moviles |= expandidos

        return desde, hasta, salidas, por_salida, todas_cedulas, todas_moviles

    @classmethod
    def elegibles(cls, desde, hasta, area="", limite=LOTE_DEFECTO, hoy=None,
                  acotar=True):
        """
        IDs de salidas que el WFM puede validar (legacy 347–396).

        Se evalúa en el MISMO orden que el legado (WFM primero, agenda
        solo como respaldo) para que el comportamiento no dependa de la
        optimización:

        1. alguna de las cédulas de la salida con actividad WFM ese día
           → elegible.
        2. si NO tiene NINGÚN registro WFM, cae al respaldo de agenda
           por cédula o por móvil.
        """
        limite = max(1, min(cls.LOTE_MAXIMO, int(limite or cls.LOTE_DEFECTO)))
        (
            desde, hasta, salidas, por_salida, cedulas, moviles,
        ) = cls._acotar_y_elegir(desde, hasta, area, limite, hoy, acotar)
        if not salidas:
            return []

        wfm = cls._presencia_wfm(cedulas, desde, hasta)
        agenda = cls._presencia_agenda(
            cedulas, moviles, desde, hasta - timedelta(days=1)
        )

        elegidos = []
        for salida in salidas:
            cedulas_salida, moviles_salida = por_salida[salida.pk]
            if any(
                (identidad, salida.fecha_salida) in wfm
                for identidad in cedulas_salida
            ):
                elegidos.append(salida.pk)
                continue
            if any(
                (identidad, salida.fecha_salida) in agenda
                for identidad in cedulas_salida
            ) or any(
                (identidad, salida.fecha_salida) in agenda
                for identidad in moviles_salida
            ):
                elegidos.append(salida.pk)
        return elegidos[:limite]

    @classmethod
    def contar_reportados(cls, desde, hasta, area="", hoy=None, acotar=True):
        """Total de ``REPORTADO`` en la ventana (legacy CountReportados)."""
        if acotar:
            desde, hasta = cls.acotar(desde, hasta, hoy)
        if desde >= hasta:
            return 0
        consulta = Salida.objects.filter(
            estado=EstadoSalida.REPORTADO,
            fecha_salida__gte=desde,
            fecha_salida__lt=hasta,
        )
        area = (area or "").strip()
        if area and area.upper() not in ("TODAS", "TODOS"):
            consulta = consulta.filter(area__iexact=area)
        return consulta.count()

    # ------------------------------------------------------------------ #
    # Lote síncrono (legacy ApplyValidationChunk 398–477)
    # ------------------------------------------------------------------ #
    @classmethod
    def aplicar_lote(cls, desde, hasta, area="", edit_cedula="",
                     limite=LOTE_DEFECTO, hoy=None, acotar=True):
        """
        Valida un lote y devuelve la respuesta legacy
        ``validarWFM`` (controlador 139–149).

        ``acotar=False`` lo usa el worker: el rango de un job ya se acotó
        al crearlo y reclamarlo de nuevo con ``hoy`` LO DESTRUYE. Es un
        defecto heredado (``ApplyValidationChunk`` 75–83 reclamps con el
        ``hoy`` del momento): un job creado el lunes y procesado el
        miércoles perdería en silencio los primeros días de su rango.
        Aquí el rango guardado en el job manda.
        """
        if acotar:
            desde, hasta = cls.acotar(desde, hasta, hoy)
        total_reportados = cls.contar_reportados(
            desde, hasta, area, hoy, acotar=False
        )
        area_respuesta = (area or "").strip().upper() or "TODAS"

        base = {
            "fecha_inicio": desde.isoformat(),
            # El legado devuelve la fecha fin INCLUSIVA (470).
            "fecha_fin": (hasta - timedelta(days=1)).isoformat(),
            "area": area_respuesta,
            "total_reportados": total_reportados,
        }
        if desde >= hasta:
            base.update(
                success=False,
                message=cls.MSG_SIN_REGISTROS,
                updated_count=0,
                selected_count=0,
                has_more_in_chunk=False,
            )
            return base

        limite = max(1, min(cls.LOTE_MAXIMO, int(limite or cls.LOTE_DEFECTO)))
        ids = cls.elegibles(desde, hasta, area, limite, hoy, acotar=False)
        if not ids:
            base.update(
                success=False,
                message=cls.MSG_SIN_REGISTROS,
                updated_count=0,
                selected_count=0,
                has_more_in_chunk=False,
            )
            return base

        with transaction.atomic():
            salidas = list(
                Salida.objects.select_for_update()
                .filter(pk__in=ids)
                .select_related("conductor")
                # Cross-BD: Empleado vive en azul, no admite JOIN (1146).
                .prefetch_related("tecnico_asignado")
            )
            # Re-filtramos por estado: otra transacción pudo haber
            # avanzado alguna fila entre la selección y este bloqueo.
            salidas = [s for s in salidas if s.estado == EstadoSalida.REPORTADO]
            actualizadas = SalidaService.validar_wfm(salidas, edit_cedula)

            # El legado vuelve a consultar con límite 1 para saber si
            # quedan más (464); aquí se hace DESPUÉS de validar, igual.
            restantes = cls.elegibles(desde, hasta, area, 1, hoy, acotar=False)

        actualizadas = len(actualizadas)
        base.update(
            success=actualizadas > 0,
            message=cls.MSG_VALIDADOS if actualizadas else cls.MSG_SIN_REGISTROS,
            updated_count=actualizadas,
            selected_count=len(ids),
            has_more_in_chunk=bool(restantes),
        )
        return base

    # ------------------------------------------------------------------ #
    # Cola de jobs (legacy CreateJob / GetJob / ClaimJob 496–671)
    # ------------------------------------------------------------------ #
    @classmethod
    def obtener_job(cls, job_uuid):
        """Job por ``job_uuid`` o None (legacy 496–506)."""
        return WfmJob.objects.filter(job_uuid=str(job_uuid or "").strip()).first()

    @classmethod
    def crear_job(cls, mes=None, yyyy=None, area="", creado_por="",
                  fecha_inicio=None, fecha_fin=None, hoy=None):
        """
        Encola un job o reutiliza el vigente (legacy 508–588).

        Devuelve ``(job, reutilizado)``. El rango se guarda INCLUSIVO en
        ``fecha_fin`` (como el legado) y el cursor arranca en
        ``fecha_inicio``.
        """
        desde, hasta = cls.resolver_rango(
            mes, yyyy, fecha_inicio, fecha_fin, hoy
        )
        area = (area or "").strip() or "TODAS"

        existente = (
            WfmJob.objects.filter(
                estado__in=[EstadoWfmJob.PENDIENTE, EstadoWfmJob.PROCESANDO],
                area=area,
                mes=int(mes or 0),
                yyyy=int(yyyy or 0),
                creado_por=str(creado_por or ""),
            )
            .order_by("-created_at")
            .first()
        )
        if existente:
            return existente, True

        total_dias = max(1, (hasta - desde).days)
        job = WfmJob.objects.create(
            job_uuid=uuid.uuid4().hex,
            estado=EstadoWfmJob.PENDIENTE,
            area=area,
            mes=int(mes or 0),
            yyyy=int(yyyy or 0),
            fecha_inicio=desde,
            # INCLUSIVO, como el legado (168: fecha_fin_inclusiva).
            fecha_fin=hasta - timedelta(days=1),
            fecha_cursor=desde,
            total_dias=total_dias,
            mensaje=cls.MSG_COLA_NUEVA,
            creado_por=str(creado_por or ""),
        )
        if not cls.obtener_job(job.job_uuid):
            raise ValueError(cls.MSG_JOB_NO_CREADO)
        return job, False

    @classmethod
    def reclamar_job(cls, job_uuid, worker_id, stale_after=None):
        """
        Toma un job pendiente/procesando si nadie lo tiene fresco
        (legacy ClaimJobByUuid 629–671 + ClaimNextJob 590–626).

        Devuelve el job reclamado o None. La exclusión mutua se logra
        con ``select_for_update``; el ``stale_after`` permite retomar un
        job cuyo worker anterior dejó de reportar.
        """
        stale_after = cls.JOB_STALE_CLAIM_SEG if stale_after is None else stale_after
        ahora = timezone.now()
        with transaction.atomic():
            job = (
                WfmJob.objects.select_for_update()
                .filter(
                    job_uuid=str(job_uuid or "").strip(),
                    estado__in=[EstadoWfmJob.PENDIENTE, EstadoWfmJob.PROCESANDO],
                )
                .first()
            )
            if job is None:
                return None
            if job.estado == EstadoWfmJob.PROCESANDO and job.locked_at:
                edad = (ahora - job.locked_at).total_seconds()
                if edad <= stale_after:
                    return None  # otro worker lo tiene
            job.estado = EstadoWfmJob.PROCESANDO
            job.locked_at = ahora
            job.locked_by = str(worker_id or "")
            job.started_at = job.started_at or ahora
            job.mensaje = "Procesando job WFM"
            job.save(
                update_fields=[
                    "estado", "locked_at", "locked_by", "started_at",
                    "mensaje", "updated_at",
                ]
            )
            return job

    @classmethod
    def reclamar_siguiente(cls, worker_id, locked_before=None):
        """
        Reclama el siguiente job de la cola (legacy ClaimNextJob 590–626).

        Candidatos: ``PENDIENTE`` o ``PROCESANDO`` sin lock fresco (el
        legacy excluye locks de menos de 10 minutos). Precedencia legada:
        un ``PROCESANDO`` huérfano se retoma antes que un ``PENDIENTE``
        nuevo (``ORDER BY estado='procesando' DESC, updated_at, id``).

        Devuelve el job reclamado o ``None`` si la cola está vacía.
        """
        ahora = timezone.now()
        locked_before = locked_before or (ahora - timedelta(minutes=10))
        with transaction.atomic():
            job = (
                WfmJob.objects.select_for_update()
                .filter(
                    estado__in=[EstadoWfmJob.PENDIENTE, EstadoWfmJob.PROCESANDO],
                )
                .filter(Q(locked_at__isnull=True) | Q(locked_at__lt=locked_before))
                .order_by(
                    # CASE WHEN estado='PROCESANDO' THEN 0 ELSE 1 END
                    Case(
                        When(estado=EstadoWfmJob.PROCESANDO, then=0),
                        default=1,
                        output_field=IntegerField(),
                    ),
                    "updated_at",
                    "id",
                )
                .first()
            )
            if job is None:
                return None
            job.estado = EstadoWfmJob.PROCESANDO
            job.locked_at = ahora
            job.locked_by = str(worker_id or "")
            job.started_at = job.started_at or ahora
            job.mensaje = "Procesando job WFM"
            job.save(
                update_fields=[
                    "estado", "locked_at", "locked_by", "started_at",
                    "mensaje", "updated_at",
                ]
            )
            return job

    @classmethod
    def procesar_job(cls, job, edit_cedula="", chunk_days=DIAS_POR_CHUNK,
                     batch_size=LOTE_POR_CHUNK):
        """
        Avanza el cursor del job UN chunk (legacy ProcessJob 674–744).

        Si el chunk no se vacía (``has_more_in_chunk``) el cursor NO
        avanza y el estado queda PROCESANDO, de modo que la siguiente
        pasada reintente el mismo día: idempotente por diseño.
        """
        if job.fecha_inicio is None or job.fecha_fin is None:
            raise ValueError(cls.MSG_JOB_RANGO)
        cursor = job.fecha_cursor or job.fecha_inicio
        fin_chunk = min(
            cursor + timedelta(days=max(1, chunk_days) - 1), job.fecha_fin
        )
        hasta_exclusiva = fin_chunk + timedelta(days=1)

        resultado = cls.aplicar_lote(
            cursor, hasta_exclusiva, job.area, edit_cedula, batch_size,
            acotar=False,
        )
        vacio = not resultado["has_more_in_chunk"]
        dias = (hasta_exclusiva - cursor).days if vacio else 0
        siguiente = fin_chunk + timedelta(days=1) if vacio else cursor
        completado = vacio and siguiente > job.fecha_fin

        job.estado = (
            EstadoWfmJob.COMPLETADO if completado else EstadoWfmJob.PROCESANDO
        )
        job.fecha_cursor = None if completado else siguiente
        job.dias_procesados = job.dias_procesados + dias
        job.total_reportados = job.total_reportados + resultado["selected_count"]
        job.total_validados = job.total_validados + resultado["updated_count"]
        job.mensaje = cls._mensaje_progreso(completado, vacio, fin_chunk)
        job.detalle_error = None
        job.locked_at = None
        job.locked_by = ""
        if completado:
            job.finished_at = timezone.now()
        job.save()
        return job

    @classmethod
    def _mensaje_progreso(cls, completado, vacio, fin_chunk):
        if completado:
            return "Validacion WFM completada"
        if vacio:
            return "Procesado hasta %s" % fin_chunk.isoformat()
        return "Procesando lote de %s" % fin_chunk.isoformat()

    @classmethod
    def fallar_job(cls, job, error):
        """Marca el job como ERROR (legacy FailJob 746–758)."""
        job.estado = EstadoWfmJob.ERROR
        job.mensaje = "El job finalizo con error"
        job.detalle_error = str(error)
        job.locked_at = None
        job.locked_by = ""
        job.finished_at = timezone.now()
        job.save()
        return job

    # ------------------------------------------------------------------ #
    # Respuesta HTTP (legacy FormatearJobRespuesta 760–798)
    # ------------------------------------------------------------------ #
    @classmethod
    def formatear_respuesta(cls, job, ahora=None, reutilizado=False,
                            worker_lanzado=False):
        """Shape exacto del JSON legacy del job (775–797) + extras."""
        ahora = ahora or timezone.now()
        total_dias = max(1, job.total_dias)
        dias = min(total_dias, job.dias_procesados)
        mensaje = job.mensaje

        if job.estado == EstadoWfmJob.PENDIENTE and not job.started_at:
            if job.updated_at and (ahora - job.updated_at).total_seconds() > cls.JOB_PENDIENTE_COLGADO_SEG:
                mensaje = cls.MSG_COLGADO_PENDIENTE
        elif job.estado == EstadoWfmJob.PROCESANDO:
            if job.updated_at and (ahora - job.updated_at).total_seconds() > cls.JOB_PROCESANDO_COLGADO_SEG:
                mensaje = cls.MSG_COLGADO_PROCESANDO

        return {
            "success": True,
            "job_uuid": job.job_uuid,
            "estado": job.estado,
            "area": job.area,
            "mes": job.mes,
            "yyyy": job.yyyy,
            "fecha_inicio": job.fecha_inicio.isoformat() if job.fecha_inicio else None,
            "fecha_fin": job.fecha_fin.isoformat() if job.fecha_fin else None,
            "fecha_cursor": job.fecha_cursor.isoformat() if job.fecha_cursor else None,
            "total_dias": total_dias,
            "dias_procesados": dias,
            "progreso": int((dias / total_dias) * 100),
            "total_reportados": job.total_reportados,
            "total_validados": job.total_validados,
            "mensaje": mensaje,
            "detalle_error": job.detalle_error,
            "creado_por": job.creado_por,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "message": (
                cls.MSG_COLA_EXISTENTE if reutilizado else cls.MSG_COLA_NUEVA
            ),
            "existing": reutilizado,
            "worker_launch_attempted": worker_lanzado,
        }
