"""
ReporteFotograficoViewSet — endpoints del reporte fotográfico diario (F3/B3).

Contrato ADMCINCO (D-A3): la vista solo enruta y resuelve identidad; toda regla
de negocio (ventana, agenda, duplicado, imágenes) vive en
ReporteFotograficoService. La identidad del responsable se deriva del usuario
autenticado (mejora sobre el legacy, que confiaba en ``dni`` doble-base64 del
cliente).

Endpoints (espejo del flujo móvil legacy):
- ``POST /reportes-fotograficos/`` → guarda el reporte + 1..5 imágenes
  (``guardar_img_reporte_vehiculo``).
- ``POST /reportes-fotograficos/validar-agenda/`` → pre-chequeo de agenda del
  responsable (``validar_agenda_responsable``).
- ``GET  /reportes-fotograficos/vehiculo-placa/?placa=`` → resuelve placa a
  vehículo (``get_info_placa``).
"""
import json

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..serializers.reporte_fotografico_serializer import (
    CrearReporteFotoSerializer,
    ReporteFotograficoQuerySerializer,
    ReporteFotograficoSerializer,
)
from ..services.reporte_fotografico_service import (
    MSG_SIN_IDENTIDAD,
    MSG_SIN_PLACA,
    ReporteFotograficoService,
)
from .paginacion import PaginacionTransporte


class ReporteFotograficoViewSet(GenericViewSet):
    permission_classes = [IsAuthenticatedOrAPIKey]
    # Obligatorio: el proyecto no define `DEFAULT_PAGINATION_CLASS`, así que
    # sin esto `self.paginator` es `None` y la respuesta revienta con 500.
    pagination_class = PaginacionTransporte

    def _responsable(self, request):
        """Resuelve el Empleado del usuario autenticado (D-A10, dos pasos)."""
        return ReporteFotograficoService.empleado_de_usuario(request.user)

    # ------------------------------------------------------------------ #
    # GET /reportes-fotograficos/ — consulta (backoffice)
    # ------------------------------------------------------------------ #
    @extend_schema(
        responses={200: ReporteFotograficoSerializer(many=True)},
        parameters=[ReporteFotograficoQuerySerializer],
        description="Listado paginado de reportes fotográficos con filtros "
                    "por rango de fechas, placa/pk y búsqueda (placa, OT, "
                    "observaciones o responsable).",
    )
    def list(self, request):
        queryset = ReporteFotograficoService.listar(request.query_params)
        page = self.paginate_queryset(queryset)
        # `page` es None solo si el paginador no está activo; con
        # `pagination_class` declarado no ocurre, pero se respeta el contrato.
        serializer = self.get_serializer(page, many=True)
        if page is None:
            return Response(serializer.data)
        return self.get_paginated_response(serializer.data)

    def get_serializer(self, *args, **kwargs):
        kwargs.setdefault("context", self.get_serializer_context())
        return ReporteFotograficoSerializer(*args, **kwargs)

    # ------------------------------------------------------------------ #
    # POST /reportes-fotograficos/ — guardar reporte + imágenes
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=CrearReporteFotoSerializer,
        responses={201: ReporteFotograficoSerializer},
        description="Guarda el reporte fotográfico diario de un vehículo "
                    "(1..5 imágenes). Valida ventana, agenda y duplicado "
                    "en servidor.",
    )
    def create(self, request):
        responsable = self._responsable(request)
        if responsable is None:
            return Response(
                {"ok": False, "error": MSG_SIN_IDENTIDAD},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CrearReporteFotoSerializer(
            data=self._payload_multipart(request)
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        vehiculo = ReporteFotograficoService.vehiculo_por_placa(datos["placa"])
        if vehiculo is None:
            return Response(
                {"ok": False, "error": MSG_SIN_PLACA},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reporte = ReporteFotograficoService.guardar(
                vehiculo=vehiculo,
                responsable=responsable,
                imagenes=datos["imagenes"],
                ot_actividad=datos.get("ot_actividad", ""),
                location=datos.get("location") or None,
                observaciones=datos.get("observaciones", ""),
                es_programacion=ReporteFotograficoService.es_programacion(
                    request.user
                ),
                actor=responsable,
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "ok": True,
                "data": ReporteFotograficoSerializer(reporte).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------ #
    # POST /reportes-fotograficos/validar-agenda/ — pre-chequeo
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=None,
        responses={200: dict},
        description="Devuelve el gate de agenda del responsable para la fecha "
                    "(hoy por defecto). Si se envía `ot_actividad`, además "
                    "valida el match OT-específica contra la agenda del día.",
    )
    @action(detail=False, methods=["post"], url_path="validar-agenda")
    def validar_agenda(self, request):
        responsable = self._responsable(request)
        if responsable is None:
            return Response(
                {"ok": False, "error": MSG_SIN_IDENTIDAD},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fecha_raw = str(request.data.get("fecha") or "").strip()
        try:
            fecha = (
                ReporteFotograficoService.hoy()
                if not fecha_raw
                else _parsear_fecha(fecha_raw)
            )
        except ValueError:
            return Response(
                {"ok": False, "error": "Fecha inválida; use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        es_programacion = ReporteFotograficoService.es_programacion(request.user)
        resultado = ReporteFotograficoService.validar_agenda_responsable(
            responsable,
            fecha,
            es_programacion=es_programacion,
        )
        resultado["fecha"] = fecha

        # Match OT-específica (pre-chequeo, solo si declara OT; el legacy la
        # validaba en un endpoint aparte — controlador_fix 175).
        ot_actividad = str(request.data.get("ot_actividad") or "").strip()
        if ot_actividad:
            check = ReporteFotograficoService.validar_agenda_ot(
                responsable, fecha, ot_actividad, es_programacion=es_programacion
            )
            resultado["ot"] = check
            resultado["tiene_agenda"] = resultado["tiene_agenda"] and check["valida"]
            if not check["valida"]:
                resultado["msg"] = check["msg"]
        return Response({"ok": True, "data": resultado})

    # ------------------------------------------------------------------ #
    # GET /reportes-fotograficos/vehiculo-placa/?placa= — resolver placa
    # ------------------------------------------------------------------ #
    @extend_schema(
        responses={200: dict},
        description="Resuelve la placa a la información del vehículo (activo).",
    )
    @action(detail=False, methods=["get"], url_path="vehiculo-placa")
    def vehiculo_placa(self, request):
        vehiculo = ReporteFotograficoService.vehiculo_por_placa(
            request.query_params.get("placa", "")
        )
        if vehiculo is None:
            return Response(
                {"ok": False, "error": MSG_SIN_PLACA},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "ok": True,
                "data": {
                    "vehiculo": {
                        "placa": vehiculo.placa,
                        "tipo_vehiculo": vehiculo.tipo_vehiculo,
                        "marca": vehiculo.marca,
                        "referencia": vehiculo.referencia,
                        "ciudad": vehiculo.ciudad_operacion,
                    }
                },
            }
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _payload_multipart(request) -> dict:
        """
        Normaliza ``request.data`` (QueryDict multipart) a un dict plano.

        La lista de imágenes requiere ``getlist``; ``location`` llega como
        string JSON desde el móvil.
        """
        data = request.data
        imagenes = (
            data.getlist("imagenes") if hasattr(data, "getlist") else data.get("imagenes", [])
        )
        location_raw = data.get("location") or ""
        try:
            location = json.loads(location_raw) if location_raw else {}
        except (TypeError, ValueError):
            location = {}
        return {
            "placa": data.get("placa", ""),
            "ot_actividad": data.get("ot_actividad", ""),
            "observaciones": data.get("observaciones", ""),
            "location": location,
            "imagenes": imagenes,
        }


def _parsear_fecha(valor: str):
    from datetime import date

    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValueError("fecha inválida")
