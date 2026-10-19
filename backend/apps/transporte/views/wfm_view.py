"""
WfmViewSet — F5-5 · validación WFM masiva.

Replica las tres acciones del controlador legacy
(`controlador_transporte_salida_informe.php` 128–214) como rutas
propias, en vez de un único ``POST`` con ``accion=``:

- ``POST /wfm/validar/``      ← ``validarWFM``       (lote síncrono)
- ``POST /wfm/crear-job/``    ← ``crearJobValidarWFM`` (cola)
- ``POST /wfm/estado-job/``   ← ``estadoJobValidarWFM`` (estado + respaldo)

MEJORA DE SEGURIDAD SOBRE EL LEGADO
-----------------------------------
Las tres acciones legacy estaban protegidas por
``validarLanzamientoVisual($visualOrigen, $launchToken)``: un HMAC
``sha256('wfm_validation_launch|' . session_id() . '|' . cedula)`` que el
propio navegador recibía en el HTML de la sábana. Ese token lo genera y
consume el MISMO cliente, así que solo impedía que otro sitio llamara
"fríamente"; no era una autorización real (cualquier sesión autenticada
podía validar salidas masivamente, incluido un operador de kiosco).

Aquí se sustituye por ``DjangoModelPermissions`` sobre ``change_salida``:
el WFM escribe en salidas, así que exige ese permiso de modelo. Es un
estrechamiento deliberado — la máquina de estados D-A11 y el gate de
gestión siguen intactos en el servicio.

El ``estado-job`` conserva el "respaldo síncrono" del legado (201–214):
si el cron/worker no ha tomado el job, la propia petición reclama y
procesa UN chunk corto, para que la visual no se quede esperando.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import EstadoWfmJob, Salida
from ..serializers import wfm_serializer
from ..services import WfmService
from .salida_view import _PermisosGestionSalida


class WfmViewSet(GenericViewSet):
    """Validación WFM masiva (cola + lote)."""

    # El WFM no da de alta salidas: las VALIDA, así que hereda el mismo
    # permiso `change_salida` que el resto de acciones de gestión.
    permission_classes = [IsAuthenticatedOrAPIKey, _PermisosGestionSalida]
    queryset = Salida.objects.all()  # DjangoModelPermissions lo exige

    # ------------------------------------------------------------------ #
    # Lote síncrono (legacy validarWFM)
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=wfm_serializer.WfmLoteSerializer,
        responses={200: dict},
        description=(
            "Valida en bloque salidas REPORTADO con respaldo WFM/agenda "
            "(legacy `validarWFM`). Solo se permite validar hoy y hasta "
            "2 días hábiles atrás. Devuelve la forma legacy "
            "(updated_count, has_more_in_chunk, total_reportados, ...)."
        ),
    )
    @action(detail=False, methods=["post"], url_path="validar")
    def validar(self, request):
        serializer = wfm_serializer.WfmLoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            # resolver_rango aplica la ventana y sus acotamientos (y
            # lanza el mensaje legacy si el periodo no es validable).
            desde, hasta = WfmService.resolver_rango(
                mes=datos["mes"],
                yyyy=datos["yyyy"],
                fecha_inicio=datos["fecha_inicio"],
                fecha_fin=datos["fecha_fin"],
            )
            resultado = WfmService.aplicar_lote(
                desde,
                hasta,
                area=datos["area"],
                edit_cedula=str(request.user.username or ""),
                limite=datos["limite"],
            )
        except ValueError as exc:
            return self._error(exc)
        return Response(resultado)

    # ------------------------------------------------------------------ #
    # Cola (legacy crearJobValidarWFM / estadoJobValidarWFM)
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=wfm_serializer.WfmCrearJobSerializer,
        responses={200: dict},
        description=(
            "Encola un job de validación WFM (legacy "
            "`crearJobValidarWFM`). Reutiliza el job vigente si ya hay "
            "uno pendiente/procesando para el mismo periodo y área."
        ),
    )
    @action(detail=False, methods=["post"], url_path="crear-job")
    def crear_job(self, request):
        serializer = wfm_serializer.WfmCrearJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            job, reutilizado = WfmService.crear_job(
                mes=datos["mes"],
                yyyy=datos["yyyy"],
                area=datos["area"],
                creado_por=str(request.user.username or ""),
            )
        except ValueError as exc:
            return self._error(exc)
        return Response(
            WfmService.formatear_respuesta(job, reutilizado=reutilizado)
        )

    @extend_schema(
        request=wfm_serializer.WfmEstadoJobSerializer,
        responses={200: dict},
        description=(
            "Estado del job (legacy `estadoJobValidarWFM`). Si sigue "
            "pendiente/procesando y ningún worker lo tomó, esta misma "
            "petición reclama y procesa UN chunk como respaldo."
        ),
    )
    @action(detail=False, methods=["post"], url_path="estado-job")
    def estado_job(self, request):
        serializer = wfm_serializer.WfmEstadoJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job_uuid = serializer.validated_data["job_uuid"]
        job = WfmService.obtener_job(job_uuid)
        if job is None:
            return self._error(WfmService.MSG_JOB_NO_ENCONTRADO, codigo=status.HTTP_404_NOT_FOUND)

        # Respaldo síncrono (legacy 201–214): si el cron no corrió, la
        # petición empuja un chunk corto en lugar de dejarlo colgado.
        if job.estado in (EstadoWfmJob.PENDIENTE, EstadoWfmJob.PROCESANDO):
            worker_id = "webwatcher:%s" % request.user.pk
            reclamado = WfmService.reclamar_job(
                job.job_uuid, worker_id, WfmService.JOB_STALE_CLAIM_SEG
            )
            if reclamado is not None:
                try:
                    job = WfmService.procesar_job(
                        reclamado,
                        edit_cedula=str(request.user.username or ""),
                        batch_size=10,
                    )
                except ValueError as exc:
                    job = WfmService.fallar_job(reclamado, exc)

        return Response(WfmService.formatear_respuesta(job))

    @staticmethod
    def _error(exc, codigo=status.HTTP_400_BAD_REQUEST):
        mensaje = str(exc)
        return Response(
            {"ok": False, "error": mensaje, "detail": mensaje},
            status=codigo,
        )

