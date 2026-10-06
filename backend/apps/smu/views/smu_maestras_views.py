from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request as DRFRequest
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.smu.models import SmuEstacion, SmuMatrizLpu
from apps.smu.serializers import SmuEstacionSerializer, SmuMatrizLpuSerializer


class SmuMaestrasPagination(PageNumberPagination):
    """Paginación para catálogo de estaciones y materiales (hasta 500 para selects/comboboxes)."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class SmuEstacionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para la consulta y búsqueda del catálogo maestro de estaciones SMU.
    Centraliza los 979 sitios normalizados en 1FN.
    """
    # sentinel seguro: evita evaluación del queryset en tiempo de importación del módulo
    queryset = SmuEstacion.objects.none()
    serializer_class = SmuEstacionSerializer
    pagination_class = SmuMaestrasPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_sitio', 'regional', 'departamento', 'municipio']
    ordering_fields = ['nombre_sitio', 'regional', 'departamento', 'tipo_estacion']

    @extend_schema(
        summary="Listar catálogo de estaciones / sitios SMU",
        description="Consulta paginada del catálogo de sitios con soporte para búsqueda y filtrado.",
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, description='Búsqueda por nombre de sitio, regional, departamento o municipio'),
            OpenApiParameter('regional', OpenApiTypes.STR, description='Filtrar por regional exacta (ej. NOROCCIDENTE, CENTRO)'),
            OpenApiParameter('tipo_estacion', OpenApiTypes.STR, description='Filtrar por tipo de estación (ej. NODO, REPETIDOR)'),
            OpenApiParameter('page_size', OpenApiTypes.INT, description='Tamaño de página (máximo 500)'),
        ],
        tags=["smu-maestras"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Obtener detalle de una estación",
        description="Consulta los atributos geográficos y técnicos normalizados de una estación por su ID.",
        tags=["smu-maestras"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        # Construir el queryset base en runtime (no en import time)
        qs = SmuEstacion.objects.filter(activo=True).order_by('nombre_sitio')
        # Guardia: drf-spectacular puede llamar este método sin request real
        if not hasattr(self, 'request') or self.request is None:
            return qs
        # Cast explícito al tipo DRF para que Pylance resuelva .query_params correctamente
        request: DRFRequest = self.request
        regional: str | None = request.query_params.get('regional')
        tipo_estacion: str | None = request.query_params.get('tipo_estacion')
        if regional and regional.strip():
            qs = qs.filter(regional__iexact=regional.strip())
        if tipo_estacion and tipo_estacion.strip():
            qs = qs.filter(tipo_estacion__iexact=tipo_estacion.strip())
        return qs


class SmuMatrizLpuViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para la consulta y búsqueda del catálogo oficial de materiales y mano de obra (Matriz LPU).
    Centraliza los 1.718 registros con precisión monetaria decimal y vigencias.
    """
    # sentinel seguro: evita evaluación del queryset en tiempo de importación del módulo
    queryset = SmuMatrizLpu.objects.none()
    serializer_class = SmuMatrizLpuSerializer
    pagination_class = SmuMaestrasPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo_sap', 'codigo_liquidacion', 'texto_sap', 'descripcion']
    ordering_fields = ['codigo_sap', 'texto_sap', 'valor_unitario']

    @extend_schema(
        summary="Listar catálogo de materiales y tarifas LPU",
        description="Consulta paginada del catálogo maestro de ítems LPU y mano de obra con valores monetarios oficiales.",
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, description='Búsqueda por código SAP, código liquidación o descripción'),
            OpenApiParameter('tipo_registro', OpenApiTypes.STR, description='Filtrar por tipo de registro (ej. material_correctivo, inventario_capex)'),
            OpenApiParameter('page_size', OpenApiTypes.INT, description='Tamaño de página (máximo 500)'),
        ],
        tags=["smu-maestras"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Obtener detalle de un ítem LPU",
        description="Consulta información detallada y tarifas de un material LPU por su ID.",
        tags=["smu-maestras"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        # Construir el queryset base en runtime (no en import time)
        qs = SmuMatrizLpu.objects.filter(activo=True).order_by('codigo_sap')
        # Guardia: drf-spectacular puede llamar este método sin request real
        if not hasattr(self, 'request') or self.request is None:
            return qs
        # Cast explícito al tipo DRF para que Pylance resuelva .query_params correctamente
        request: DRFRequest = self.request
        tipo_registro: str | None = request.query_params.get('tipo_registro')
        if tipo_registro and tipo_registro.strip():
            qs = qs.filter(tipo_registro__iexact=tipo_registro.strip())
        return qs
