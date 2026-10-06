from rest_framework import mixins, status, filters, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db import IntegrityError
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

import logging

from apps.smu.export import (
    CONTENT_TYPE_XLSX,
    ExporteNoSoportado,
    generar_excel_actividad,
)
from apps.smu.models import SmuActividad
from apps.smu.serializers import SmuActividadSerializer
from apps.smu.serializers import SmuActividadListSerializer
from apps.smu.services import crear_actividad_smu

logger = logging.getLogger(__name__)


class SmuActividadPagination(PageNumberPagination):
    """Paginación estándar: 25 filas por página, máximo 100."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class SmuActividadViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API del módulo SMU.

    - ``POST /smu/actividades/`` — crea una actividad con todas sus subtablas.
    - ``GET  /smu/actividades/`` — listado paginado con filtros (historial).
    - ``GET  /smu/actividades/<id>/`` — detalle completo de una actividad.
    - ``GET  /smu/actividades/<id>/export/`` — descarga el formulario en Excel.
    """

    queryset = SmuActividad.objects.all().order_by("-id")
    pagination_class = SmuActividadPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre_estacion", "codigo_ot", "responsable_cedula", "responsable_nombre"]
    ordering_fields = ["id", "fecha_inicio", "created_at"]
    ordering = ["-id"]

    def get_serializer_class(self):
        if self.action == "list":
            return SmuActividadListSerializer
        return SmuActividadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs.select_related("estacion", "responsable", "actividad_operaciones")
        if self.action == "retrieve":
            return qs.select_related("estacion", "responsable", "actividad_operaciones").prefetch_related(
                "tecnicos",
                "materiales__material_lpu",
                "evidencias",
                "transportes",
                "firmas_cierre",
                "certificados",
            )
        return qs

    # ── GET /smu/actividades/ ───────────────────────────────────────────────

    @extend_schema(
        summary="Listar actividades SMU (historial)",
        description=(
            "Devuelve el historial paginado de actividades registradas. "
            "Soporta búsqueda por estación, OT, cédula y nombre del responsable. "
            "Filtros adicionales por categoría y tipo de formulario."
        ),
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR, description="Busca en estación, OT, responsable"),
            OpenApiParameter("categoria", OpenApiTypes.STR, description="Filtro por categoría (preventivos, correctivos_capex…)"),
            OpenApiParameter("tipo_formulario", OpenApiTypes.STR, description="Filtro por tipo (planta, tipologia1…)"),
            OpenApiParameter("estado", OpenApiTypes.STR, description="Filtro por estado (enviado, aprobado…)"),
            OpenApiParameter("page", OpenApiTypes.INT, description="Número de página"),
            OpenApiParameter("page_size", OpenApiTypes.INT, description="Filas por página (máx. 100)"),
        ],
        tags=["smu"],
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()

        # Filtros exactos opcionales
        for field in ("categoria", "tipo_formulario", "estado"):
            val = request.query_params.get(field)
            if val:
                qs = qs.filter(**{field: val})

        # Búsqueda de texto
        qs = self.filter_queryset(qs)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # ── POST /smu/actividades/ ──────────────────────────────────────────────

    @extend_schema(
        summary="Crear reporte de actividad SMU",
        description=(
            "Único punto de entrada de creación. Crea una actividad cabecera con "
            "sus subtablas asociadas (técnicos, materiales, evidencias, "
            "transportes, detalle AA/Planta/Falla/CAPEX) en una transacción "
            "atómica."
        ),
        tags=["smu"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            actividad = crear_actividad_smu(serializer.validated_data)
        except IntegrityError as e:
            return Response(
                {"detail": f"Error de integridad en los datos: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_serializer = self.get_serializer(actividad)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── GET /smu/actividades/<id>/export/ ────────────────────────────────────

    @extend_schema(
        summary="Exportar el formulario a Excel",
        description=(
            "Descarga la actividad en el formato (estilo) de su formulario. "
            "El contenido se adapta a los datos guardados: una fila por "
            "material, un bloque de fotos por cada dos evidencias y bloques de "
            "texto con la altura del contenido. Los tipos de formulario sin "
            "plantilla devuelven 400."
        ),
        tags=["smu"],
        responses={(200, CONTENT_TYPE_XLSX): OpenApiTypes.BINARY},
    )
    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request, pk=None):
        actividad = self.get_object()

        try:
            contenido, nombre_archivo = generar_excel_actividad(actividad)
        except ExporteNoSoportado as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Error generando el Excel de la actividad #%s", actividad.pk)
            return Response(
                {"detail": "No se pudo generar el archivo Excel de este formulario."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(contenido, content_type=CONTENT_TYPE_XLSX)
        response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        response["Content-Length"] = str(len(contenido))
        return response
