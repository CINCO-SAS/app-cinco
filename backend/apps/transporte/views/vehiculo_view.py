"""
VehiculoViewSet — ABM de la flota vehicular (Tab Base Transportadores).

Contrato ADMCINCO (D-A3): delega en FlotaService; traduce sus ValueError
a HTTP 400/404, igual que el resto del módulo.
"""
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Vehiculo
from ..serializers import vehiculo_serializer
from ..services import FlotaService
from .paginacion import PaginacionTransporte


class VehiculoViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Listado/detalle de vehículos + escritura (crear/actualizar/inactivar)
    y acciones de flota: ficha documental y subida de documentos.
    """

    queryset = Vehiculo.objects.all()
    pagination_class = PaginacionTransporte
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ["placa", "marca", "referencia", "numero_motor", "numero_vin"]

    def get_serializer_class(self):
        if self.action == "list":
            return vehiculo_serializer.VehiculoListSerializer
        return vehiculo_serializer.VehiculoSerializer

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        try:
            queryset = FlotaService.listar(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            FlotaService.obtener(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @extend_schema(request=vehiculo_serializer.VehiculoSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            vehiculo = FlotaService.crear(
                serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            vehiculo_serializer.VehiculoSerializer(vehiculo).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=vehiculo_serializer.VehiculoSerializer)
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parche = kwargs.pop("partial", False)
        try:
            vehiculo = FlotaService.actualizar(
                kwargs["pk"],
                serializer.validated_data,
                actor=self._actor(request),
                parche=parche,
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(vehiculo_serializer.VehiculoSerializer(vehiculo).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    # ------------------------------------------------------------------ #
    # Acciones de flota
    # ------------------------------------------------------------------ #
    @extend_schema(
        responses={200: vehiculo_serializer.VehiculoSerializer},
        description="Ficha con semáforo SOAT/CDA calculado en servidor (B8).",
    )
    @action(detail=True, methods=["get"], url_path="resumen")
    def resumen(self, request, pk=None):
        try:
            ficha = FlotaService.ficha_documental(pk)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            vehiculo_serializer.VehiculoSerializer(ficha["vehiculo"]).data
            | {"semaforo": ficha["semaforo"]}
        )

    @extend_schema(
        request=vehiculo_serializer.DocumentoVehiculoSerializer,
        responses={200: vehiculo_serializer.DocumentoVehiculoSerializer},
        description="Sube o reemplaza un documento (upsert por tipo, §5.3).",
    )
    @action(detail=True, methods=["post"], url_path="documentos")
    def documentos(self, request, pk=None):
        serializer = vehiculo_serializer.DocumentoVehiculoSerializer(
            data={**request.data, "vehiculo": pk}
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            documento = FlotaService.subir_documento(
                vehiculo_id=pk,
                tipo=datos["tipo"],
                archivo=datos.get("archivo"),
                fecha_vencimiento=datos.get("fecha_vencimiento"),
                actor=self._actor(request),
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(
            vehiculo_serializer.DocumentoVehiculoSerializer(documento).data
        )

    @extend_schema(
        request={"multipart/form-data": {"type": "object", "properties": {
            "archivo": {"type": "string", "format": "binary"},
        }}},
        responses={200: None},
        description=(
            "Import CSV bancarios (CR-13): auto-detección de separador, "
            "limpieza alfanumérica y upsert por placa."
        ),
    )
    @action(detail=False, methods=["post"], url_path="importar-bancarios")
    def importar_bancarios(self, request):
        archivo = request.FILES.get("archivo")
        try:
            resultado = FlotaService.importar_datos_bancarios_csv(
                archivo, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        http = (
            status.HTTP_200_OK
            if resultado["insertados"] + resultado["actualizados"] > 0
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(resultado, status=http)

    @extend_schema(
        responses={(200, "image/png"): OpenApiTypes.BYTE},
        description=(
            "QR de verificación de la placa, persistido en media/transporte/codigos-qr/ "
            "y en el campo codigo_qr del vehículo."
        ),
    )
    @action(detail=True, methods=["get"], url_path="qr.png")
    def qr(self, request, pk=None):
        try:
            png = FlotaService.generar_qr(pk)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return HttpResponse(png, content_type="image/png")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _actor(request):
        return getattr(request.user, "empleado", None)
