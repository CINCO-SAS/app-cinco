"""
ReporteFotograficoService — núcleo del reporte fotográfico diario (F3/B3).

Legacy verificado (P1 resuelto):
- transporte_reporte_vehiculo_inc.php: ventana 10:00–16:00 America/Bogota
  (``permitirReporteHastaLas16``), límite 1–5 imágenes, mensajes de error.
- controlador_transporte_img_reporte_salida_fix.php: ``validar_agenda_responsable``
  (agenda en ``operaciones_agenda`` + exención de área), ``transporteOmiteValidacionOt``
  y save ``guardar_img_reporte_vehiculo``.

MEJORAS sobre el legacy (usado como guía de comportamiento, endurecido en servidor):
1. **Identidad**: el legacy confiaba en ``dni`` = ``btoa(btoa(cedula))`` del
   cliente (falsa identidad). Aquí el responsable se deriva del usuario
   autenticado (``username`` == ``cedula``); el cliente NO envía cédula.
2. **Ventana en servidor**: el legacy validaba 10:00–16:00 SOLO en JavaScript
   (bypassable por POST). Aquí ``en_ventana`` corre dentro de ``guardar``.
3. **Agenda en servidor**: el legacy validaba la agenda en un endpoint aparte y
   el save NO la re-verificaba. Aquí ``validar_agenda_responsable`` corre dentro
   de ``guardar``.
4. **Imágenes**: el legacy validaba solo la extensión por string; aquí Pillow
   decodifica y re-codifica (1280px / q0.7), rechazando archivos no-decodificables.
5. Queries ORM parametrizadas (sin riesgo de inyección) y lookup de personal por
   ``cedula`` (única), no ``ORDER BY cargo DESC``.

Paridad conservada (comportamiento + mensajes legacy literales):
- Ventana inclusive [10:00, 16:00]; exención de área (O&M, I&M apoyo, Pymes EN,
  programación); gate "¿tiene agenda hoy?"; **match OT-específica**
  (``validar_agenda_ot``, port de ``validarOtActividadTransporte`` +
  ``validarOtActividadAgendaTransporte``); 1–5 imágenes; un reporte por
  (vehículo, fecha, técnico).

Pendiente documentado (no en este bloque, requiere decisión de diseño):
- Ventana de días anteriores con excepción en ``programacion_parametros``
  (``excepciones_reporte_dias_anteriores``: ``{cedula, fecha_permitida}``) →
  storage propio + CRUD con ``puede_programar`` + ETL de las excepciones
  existentes. Hoy el backend rechaza toda fecha pasada.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, time
from io import BytesIO
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from apps.empleados.models import Empleado
from apps.operaciones.models import Agenda  # SOLO LECTURA (módulo ajeno)

from ..models import (
    EstadoSalida,
    ReporteFotograficoVehiculo,
    ReporteFotoImagen,
    Salida,
    Vehiculo,
)

# Zona horaria del reporte (legacy usa America/Bogota explícitamente).
ZONA_REPORTE = ZoneInfo("America/Bogota")

# Ventana de captura (transporte_reporte_vehiculo_inc.php 1232–1262):
# ``permitirReporteHastaLas16 = true`` → fin 16:00 (fallback histórico 13:00).
HORA_INICIO_VENTANA = time(10, 0)
HORA_FIN_VENTANA = time(16, 0)

# Límites de imagen (frontend: 5 máx, 3MB; compresión 1280px/q0.7 → ~500–800KB).
MAX_IMAGENES = 5
MAX_BYTES_IMAGEN = 3 * 1024 * 1024
MAX_ANCHO_IMAGEN = 1280
CALIDAD_IMAGEN = 70

# Mensajes legacy literales (transporte_reporte_vehiculo_inc.php /
# controlador_transporte_img_reporte_salida_fix.php).
MSG_SIN_AGENDA = "Sin agenda programada para hoy. No es posible guardar el reporte."
MSG_AGENDA_EXENTA = (
    "Validación de agenda no requerida para el área/cargo de este empleado."
)
MSG_SIN_IDENTIDAD = "No fue posible identificar al empleado del reporte."
MSG_SIN_AGENDA_TECNICO = "El responsable no tiene agenda programada para el día de hoy."
MSG_FUERA_VENTANA = (
    "Por ahora, solo puedes tomar fotos entre las 10:00 a.m. y las 4:00 p.m."
)
MSG_MAX_IMAGENES = "Error. No puede subir más de 5 imagenes por reporte."
MSG_MIN_IMAGENES = "Error. Debe seleccionar al menos una imagen para subir."
MSG_DUPLICADO = (
    "Ya existe un reporte completo para este vehículo por este técnico "
    "en la fecha seleccionada"
)
MSG_SIN_PLACA = "Error. Debe seleccionar una placa válida antes de guardar el reporte."
MSG_FECHA_PASADA = (
    "No tiene autorización ni excepción activa para guardar un reporte con "
    "fecha {fecha}."
)
MSG_IMAGEN_INVALIDA = "El archivo adjunto no es una imagen válida."
MSG_OT_VACIA = "Debe indicar la OT / actividad."
MSG_OT_VACIA_WFM = "Debe ingresar una de las OT asignadas para el dia de hoy."
MSG_OT_NO_AGENDADA = (
    "La OT / actividad {ot} no está agendada para el empleado {cedula} "
    "en la fecha {fecha}."
)


class ReporteFotograficoService:
    """Operaciones del reporte fotográfico diario (F3/B3)."""

    # ------------------------------------------------------------------ #
    # Utilidades de identidad / normalización (pure, testable)
    # ------------------------------------------------------------------ #
    @staticmethod
    def normalizar_clave(valor) -> str:
        """``transporteNormalizarClaveEmpleado``: mayúsculas y solo [A-Z0-9]."""
        return re.sub(r"[^A-Z0-9]", "", str(valor or "").upper())

    @staticmethod
    def empleado_de_usuario(user) -> Empleado | None:
        """
        Resuelve el ``Empleado`` (azul) desde el usuario autenticado.

        D-A10: dos pasos sin JOIN cross-DB (``username`` == ``cedula``).
        """
        if isinstance(user, AnonymousUser):
            return None
        cedula = getattr(user, "username", None)
        if not cedula:
            return None
        return Empleado.objects.filter(cedula=cedula).first()

    @staticmethod
    def es_programacion(user) -> bool:
        """
        ¿Es programación/admin? (§5.9 / E3): delega en PermisoService.
        """
        from .permiso_service import PermisoService

        return PermisoService.puede_programar(user)

    @classmethod
    def normalizar_ot_actividad(cls, ot, area="", carpeta="") -> str:
        """``transporteNormalizarOtActividad`` (controlador 89–109)."""
        ot_n = str(ot or "").upper().strip()
        if not ot_n:
            return ""
        area_n = cls.normalizar_clave(area)
        carpeta_n = cls.normalizar_clave(carpeta)
        requiere = area_n == "IM" or (area_n == "EN" and carpeta_n == "PYMESEN")
        if not requiere:
            return ot_n
        base = ot_n.split("_", 1)[0].strip()
        digitos = re.sub(r"\D", "", base)
        return digitos or base

    @staticmethod
    def _texto_comparable(valor) -> str:
        """``transporteTextoComparableAgenda`` (controlador 74–82): mayúsculas
        y espacios colapsados; el legacy comparaba exacto con esto."""
        texto = str(valor or "").upper().strip()
        return re.sub(r"\s+", " ", texto) if texto else ""

    @classmethod
    def omite_validacion_ot(cls, area="", carpeta="", cargo="") -> bool:
        """``transporteOmiteValidacionOt`` (controlador 117–142)."""
        a = cls.normalizar_clave(area)
        c = cls.normalizar_clave(carpeta)
        g = cls.normalizar_clave(cargo)
        omite_oy_m = a == "OM" and any(
            x in c for x in ("CORRECTIVO", "MANTENIMIENTO", "MPF")
        )
        omite_iym = a == "IM" and "APOYO" in c and (
            "APOYOEXTERNO" in g or "APOYOEXT" in g
        )
        omite_pymes = a == "EN" and ("PYMES" in c or "PYMESEN" in c)
        return omite_oy_m or omite_iym or omite_pymes

    @classmethod
    def valida_ot_en_wfm(cls, area="") -> bool:
        """``transporteValidaOtEnWfm`` (controlador 111–115): área == IM."""
        return cls.normalizar_clave(area) == "IM"

    # ------------------------------------------------------------------ #
    # Reloj (America/Bogota) + ventana de captura
    # ------------------------------------------------------------------ #
    @classmethod
    def ahora_local(cls) -> datetime:
        return timezone.now().astimezone(ZONA_REPORTE)

    @classmethod
    def hoy(cls) -> date:
        return cls.ahora_local().date()

    @classmethod
    def en_ventana(cls, ahora: datetime | None = None) -> bool:
        """
        ¿Está la hora local (Bogotá) dentro de [10:00, 16:00] inclusive?

        Corre EN SERVIDOR (el legacy solo lo validaba en el navegador).
        """
        local = (ahora or cls.ahora_local()).astimezone(ZONA_REPORTE)
        hora = local.time()
        return HORA_INICIO_VENTANA <= hora <= HORA_FIN_VENTANA

    # ------------------------------------------------------------------ #
    # Agenda (lectura de operaciones_agenda — módulo ajeno)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _agendas_del_dia(empleado: Empleado, fecha: date) -> list:
        """
        Agendas no borradas que cubren ``fecha`` para el técnico.

        SOLO LECTURA de ``operaciones_agenda`` (operaciones → DB default).
        Dos pasos sin JOIN cross-DB: el ``Empleado`` (azul) ya resolvió la cédula.
        """
        cedula = getattr(empleado, "cedula", None)
        if not cedula:
            return []
        return list(
            Agenda.objects.filter(
                responsable__username=cedula,
                fecha_inicio__lte=fecha,
                fecha_fin__gte=fecha,
                is_deleted=False,
            ).select_related("actividad", "actividad__detalle")[:20]
        )

    @classmethod
    def _agenda_coincide_con_ot(cls, agenda: Agenda, comparable: str) -> bool:
        """
        ``validarOtActividadAgendaTransporte`` (controlador 221–237).

        La OT digitada coincide si su texto comparable es EXACTAMENTE igual
        a ``actividad.ot``, ``detalle.tipo_trabajo``, ``detalle.descripcion``
        u ``observacion`` de la agenda.
        """
        actividad = getattr(agenda, "actividad", None)
        detalle = getattr(actividad, "detalle", None) if actividad else None
        candidatos = (
            getattr(actividad, "ot", ""),
            getattr(detalle, "tipo_trabajo", "") if detalle else "",
            getattr(detalle, "descripcion", "") if detalle else "",
            agenda.observacion,
        )
        return any(
            texto and cls._texto_comparable(texto) == comparable
            for texto in candidatos
        )

    @staticmethod
    def _agenda_a_dict(agenda: Agenda) -> dict:
        actividad = getattr(agenda, "actividad", None)
        return {
            "ot": getattr(actividad, "ot", "") if actividad else "",
            "nombre": getattr(actividad, "nombre", "") if actividad else "",
            "fecha_inicio": agenda.fecha_inicio,
            "fecha_fin": agenda.fecha_fin,
        }

    @classmethod
    def validar_agenda_responsable(
        cls, empleado: Empleado | None, fecha: date, es_programacion: bool = False
    ) -> dict:
        """
        Gate de agenda del responsable (``validar_agenda_responsable`` legacy).

        Devuelve ``{tiene_agenda, origen, agendas, msg}``. La exención de área o
        programación se marca ``origen='area_exenta'`` y NO exige agenda.
        """
        if empleado is None:
            return {
                "tiene_agenda": False,
                "origen": "sin_identidad",
                "agendas": [],
                "msg": MSG_SIN_IDENTIDAD,
            }
        area = getattr(empleado, "area", "") or ""
        carpeta = getattr(empleado, "carpeta", "") or ""
        cargo = getattr(empleado, "cargo", "") or ""
        if es_programacion or cls.omite_validacion_ot(area, carpeta, cargo):
            return {
                "tiene_agenda": True,
                "origen": "area_exenta",
                "agendas": [],
                "msg": MSG_AGENDA_EXENTA,
            }
        agendas = cls._agendas_del_dia(empleado, fecha)
        if not agendas:
            return {
                "tiene_agenda": False,
                "origen": "agenda",
                "agendas": [],
                "msg": MSG_SIN_AGENDA_TECNICO,
            }
        return {
            "tiene_agenda": True,
            "origen": "agenda",
            "agendas": [cls._agenda_a_dict(a) for a in agendas],
            "msg": "",
        }

    # ------------------------------------------------------------------ #
    # Match OT-específica (refinamiento B3 diferido)
    # ------------------------------------------------------------------ #
    @classmethod
    def validar_agenda_ot(
        cls,
        empleado: Empleado | None,
        fecha: date,
        ot: str,
        es_programacion: bool = False,
    ) -> dict:
        """
        Port de ``validarOtActividadTransporte`` +
        ``validarOtActividadAgendaTransporte``
        (controlador_transporte_img_reporte_salida_fix.php 319–360 y 175–244).

        Reglas, en orden:
        1. Área exenta o permiso de programación → no se valida nada.
        2. Sin OT digitada → error (mensaje distinto si el área valida en
           WFM, que exige una OT del día).
        3. Área que valida en WFM (``area == 'IM'``) → se recibe la OT sin
           validarla: la validación queda diferida al subsistema WFM.
        4. Resto: la OT debe coincidir EXACTAMENTE (texto comparable) con
           ``actividad.ot`` / ``tipo_trabajo`` / ``descripcion`` /
           ``observacion`` de alguna agenda del día del responsable.

        Devuelve ``{valida, origen, ot, msg, agendas}``.
        """
        area = getattr(empleado, "area", "") or ""
        carpeta = getattr(empleado, "carpeta", "") or ""
        cargo = getattr(empleado, "cargo", "") or ""
        cedula = getattr(empleado, "cedula", "") or ""

        if es_programacion or cls.omite_validacion_ot(area, carpeta, cargo):
            return {
                "valida": True,
                "origen": "area_exenta",
                "ot": "",
                "msg": MSG_AGENDA_EXENTA,
                "agendas": [],
            }

        ot_n = cls.normalizar_ot_actividad(ot, area, carpeta)
        if not ot_n:
            return {
                "valida": False,
                "origen": "ot_vacia",
                "ot": "",
                "msg": MSG_OT_VACIA_WFM if cls.valida_ot_en_wfm(area) else MSG_OT_VACIA,
                "agendas": [],
            }

        if cls.valida_ot_en_wfm(area):
            # La validación de IM pasa por WFM (subsistema aparte, F5).
            return {
                "valida": True,
                "origen": "wfm",
                "ot": ot_n,
                "msg": "",
                "agendas": [],
            }

        agendas = cls._agendas_del_dia(empleado, fecha)
        comparable = cls._texto_comparable(ot_n)
        if any(cls._agenda_coincide_con_ot(a, comparable) for a in agendas):
            return {
                "valida": True,
                "origen": "agenda",
                "ot": ot_n,
                "msg": "",
                "agendas": [cls._agenda_a_dict(a) for a in agendas],
            }
        return {
            "valida": False,
            "origen": "agenda",
            "ot": ot_n,
            "msg": MSG_OT_NO_AGENDADA.format(ot=ot_n, cedula=cedula, fecha=fecha),
            "agendas": [cls._agenda_a_dict(a) for a in agendas],
        }

    # ------------------------------------------------------------------ #
    # Imágenes (Pillow): validación + compresión
    # ------------------------------------------------------------------ #
    @classmethod
    def validar_imagenes(cls, imagenes) -> None:
        """Lanza ``ValueError`` con el mensaje legacy si el conteo es inválido."""
        imagenes = list(imagenes or [])
        if not imagenes:
            raise ValueError(MSG_MIN_IMAGENES)
        if len(imagenes) > MAX_IMAGENES:
            raise ValueError(MSG_MAX_IMAGENES)

    @staticmethod
    def comprimir_imagen(archivo) -> ContentFile:
        """
        Decodifica con Pillow, escala a ≤1280px de ancho y re-codifica JPEG q0.7.

        Rechaza archivos que no sean imágenes decodificables (mejora sobre el
        legacy, que solo revisaba la extensión).
        """
        try:
            img = Image.open(archivo)
            img.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValueError(MSG_IMAGEN_INVALIDA)
        if img.mode in ("RGBA", "P", "LA", "CMYK"):
            img = img.convert("RGB")
        ancho, alto = img.size
        if ancho > MAX_ANCHO_IMAGEN:
            ratio = MAX_ANCHO_IMAGEN / ancho
            img = img.resize(
                (MAX_ANCHO_IMAGEN, max(1, int(alto * ratio))), Image.LANCZOS
            )
        salida = BytesIO()
        img.save(salida, format="JPEG", quality=CALIDAD_IMAGEN, optimize=True)
        salida.seek(0)
        nombre = os.path.basename(getattr(archivo, "name", "") or "reporte.jpg")
        base, _ = os.path.splitext(nombre)
        return ContentFile(salida.getvalue(), name=f"{base}.jpg")

    # ------------------------------------------------------------------ #
    # Guardado transaccional
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def guardar(
        cls,
        *,
        vehiculo: Vehiculo,
        responsable: Empleado,
        imagenes,
        ot_actividad: str = "",
        fecha: date | None = None,
        location: dict | None = None,
        observaciones: str = "",
        es_programacion: bool = False,
        actor: Empleado | None = None,
    ) -> ReporteFotograficoVehiculo:
        """
        Guarda un reporte fotográfico con sus 1..5 imágenes.

        Valida EN SERVIDOR: conteo de imágenes, ventana horaria, gate de agenda
        y duplicado por (vehículo, fecha, técnico). Devuelve el reporte creado.
        Lanza ``ValueError`` con el mensaje legacy ante la primera violación.
        """
        if vehiculo is None:
            raise ValueError(MSG_SIN_PLACA)
        cls.validar_imagenes(imagenes)

        fecha = fecha or cls.hoy()
        # Ventana de captura (servidor; el legacy solo en JS).
        if not cls.en_ventana():
            raise ValueError(MSG_FUERA_VENTANA)
        # Días anteriores: aún sin excepciones ETL → solo hoy (o futuro).
        if fecha < cls.hoy():
            raise ValueError(MSG_FECHA_PASADA.format(fecha=fecha))
        # Agenda del responsable (servidor; el legacy solo en JS/endpoint aparte).
        agenda = cls.validar_agenda_responsable(responsable, fecha, es_programacion)
        if not agenda["tiene_agenda"]:
            raise ValueError(agenda["msg"] or MSG_SIN_AGENDA)
        # Match OT-específica (legacy `validarOtActividadTransporte`): si el
        # reporte declara una OT, debe estar agendada para ese técnico/fecha.
        validacion_ot = {
            "agenda_origen": agenda.get("origen"),
            "agenda_exenta": agenda.get("origen") == "area_exenta",
            "ot": ot_actividad or "",
        }
        if ot_actividad:
            check = cls.validar_agenda_ot(
                responsable, fecha, ot_actividad, es_programacion
            )
            validacion_ot["ot_origen"] = check["origen"]
            validacion_ot["ot_valida"] = check["valida"]
            if not check["valida"]:
                raise ValueError(check["msg"])
        # Duplicado (vehículo, fecha, técnico).
        if ReporteFotograficoVehiculo.objects.filter(
            vehiculo=vehiculo, fecha=fecha, responsable=responsable
        ).exists():
            raise ValueError(MSG_DUPLICADO)

        creador = actor or responsable
        # Comprimir ANTES de escribir en BD (fail-fast): si un archivo no es
        # imagen, no queda ni cabecera de reporte.
        procesadas = [
            (
                os.path.basename(getattr(archivo, "name", "") or ""),
                cls.comprimir_imagen(archivo),
            )
            for archivo in imagenes
        ]
        reporte = ReporteFotograficoVehiculo.objects.create(
            vehiculo=vehiculo,
            responsable=responsable,
            fecha=fecha,
            hora=cls.ahora_local().time(),
            ot_actividad=ot_actividad or None,
            validacion_ot=validacion_ot,
            location=location or None,
            observaciones=observaciones or "",
            creado_por=creador,
        )
        for nombre, contenido in procesadas:
            ReporteFotoImagen.objects.create(
                reporte=reporte,
                imagen=contenido,
                nombre_original=nombre,
                creado_por=creador,
            )
        # B14: al haber evidencia, el badge REPORTE de la salida del día pasa
        # a "Sí" (es lo que hacía `datos.reporte` en el JSON del legacy).
        cls.marcar_salida_reportada(vehiculo, fecha)
        return reporte

    # ------------------------------------------------------------------ #
    # B14 · el badge REPORTE de la salida
    # ------------------------------------------------------------------ #
    @staticmethod
    def marcar_salida_reportada(vehiculo, fecha) -> int:
        """Pone ``Salida.reportado = True`` en las salidas de ese día (B14).

        **Por qué existía esto antes**: en el legacy el reporte se escribía
        dentro del JSON ``datos`` de la fila de salida (``datos.reporte`` /
        ``datos.reportes_adicionales``) y el badge salía de ahí
        (``base_salida_transporte.php`` 2209). La migración aplanó ese JSON
        al campo ``reportado`` pero **nada lo activaba**: el badge B14 quedó
        pintando "No" eternamente.

        Dos decisiones deliberadas:
        * NO es obligatorio que exista la salida. El reporte fotográfico es
          evidencia del vehículo y puede haberse capturado el mismo día sin
          salida registrada; ahí simplemente no hay fila que marcar.
        * Se usa ``update()`` de una sola pasada (1 query) en vez de
          ``save()`` por fila: solo cambia un booleano y no queremos que
          actualizar el badge dispare el guardado completo de la fila.
        * Se excluyen ELIMINADAS (un reporte no revive una salida borrada)
          y las que ya estaban marcadas (evita un UPDATE sin cambios).
        """
        return (
            Salida.objects.filter(vehiculo=vehiculo, fecha_salida=fecha)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .exclude(reportado=True)
            .update(reportado=True)
        )

    # ------------------------------------------------------------------ #
    # Consulta del backoffice
    # ------------------------------------------------------------------ #
    @classmethod
    def listar(cls, query_params):
        """Queryset de reportes con filtros, listo para serializar.

        cross-DB: ``vehiculo`` vive en transporte y ``responsable`` en
        **azul** (router ``empleados → azul``), así que SOLO se traen con
        ``select_related`` (mismo origen, el JOIN es válido) +
        ``prefetch_related`` respectivamente. Un ``select_related`` sobre
        ``responsable`` generaría un JOIN hacia la tabla de OTRA base y
        revienta contra MySQL real (los tests en SQLite no lo ven, porque
        ahí el router está vacío).
        """
        desde = (query_params.get("desde") or "").strip()
        hasta = (query_params.get("hasta") or "").strip()
        vehiculo = (query_params.get("vehiculo") or "").strip()
        search = (query_params.get("search") or "").strip()

        # `vehiculo` acepta placa (lo normal) o pk, igual que en Salidas.
        filtro_vehiculo: dict = {}
        if vehiculo:
            if vehiculo.isdigit():
                filtro_vehiculo = {"vehiculo_id": int(vehiculo)}
            else:
                filtro_vehiculo = {"vehiculo__placa__iexact": vehiculo}

        queryset = ReporteFotograficoVehiculo.objects.select_related(
            "vehiculo"
        ).prefetch_related("responsable", "imagenes")

        if desde:
            queryset = queryset.filter(fecha__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha__lte=hasta)
        if filtro_vehiculo:
            queryset = queryset.filter(**filtro_vehiculo)

        if search:
            # La búsqueda toca columnas de AMBOS orígenes. Placa/OT/
            # observaciones viven en transporte y se filtran en la misma
            # consulta; el cédula/nombre vive en azul, así que se resuelve
            # ANTES como lista de PKs y luego se compara por id (2 queries,
            # nunca un JOIN cruzado).
            #
            # Cada PALABRA debe encajar en algún campo del empleado. Así
            # "API TEST" (nombre + apellido en columnas distintas) encuentra
            # al empleado, mientras que un solo `icontains` sobre el nombre
            # no lo haría.
            personas = Empleado.objects.all()
            for palabra in [p for p in search.split() if p]:
                personas = personas.filter(
                    Q(cedula__icontains=palabra)
                    | Q(nombre__icontains=palabra)
                    | Q(apellido__icontains=palabra)
                )
            ids_personas = list(personas.values_list("pk", flat=True)[:500])

            queryset = queryset.filter(
                Q(vehiculo__placa__icontains=search)
                | Q(ot_actividad__icontains=search)
                | Q(observaciones__icontains=search)
                | Q(responsable_id__in=ids_personas)
            )

        # Más recientes primero (fecha > hora > id desempata).
        return queryset.order_by("-fecha", "-hora", "-id")

    # ------------------------------------------------------------------ #
    # Resolución de vehículo
    # ------------------------------------------------------------------ #
    @staticmethod
    def vehiculo_por_placa(placa: str) -> Vehiculo | None:
        """Resuelve el vehículo activo por placa (exacta, en mayúsculas)."""
        placa = str(placa or "").strip().upper()
        if not placa:
            return None
        return Vehiculo.objects.filter(placa=placa, activo=True).first()
