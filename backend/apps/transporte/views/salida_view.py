"""
SalidaViewSet — alta y consulta de salidas (matriz S6 + B1).

Contrato ADMCINCO (D-A3): delega en SalidaService y traduce sus
ValueError a HTTP 400/404.

Endpoint:
- `POST /salidas/` (S6): alta con ventana CR-9, anticolisión CR-1/CR-2 y
  exigencia de personal — todo en el servicio.
- `GET /salidas/?desde=&hasta=&estado=&...` (B1): filtros server-side.
- `GET /salidas/{id}/`: detalle con snapshots.

Las transiciones (aprobar/rechazar/validar/eliminar) y novedades son
B4 (F4 backoffice); la máquina de estados vive hoy en SalidaService.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import Salida
from ..serializers import salida_serializer
from ..services import SalidaService


class SalidaViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Lectura a autenticados; alta requiere `transporte.add_salida`
    (DjangoModelPermissions: GET sin permiso de modelo, POST con add)."""

    queryset = Salida.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey, DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        try:
            salidas = SalidaService.listar(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(salidas)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            salida = SalidaService.obtener(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(self.get_serializer(salida).data)

    @extend_schema(request=salida_serializer.RegistrarSalidaSerializer)
    def create(self, request, *args, **kwargs):
        serializer = salida_serializer.RegistrarSalidaSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        try:
            salida = SalidaService.registrar_salida(
                serializer.validated_data, usuario=request.user
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Salida.DoesNotExist:
            return Response(
                {"detail": "vehículo inexistente"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            salida_serializer.SalidaSerializer(salida).data,
            status=status.HTTP_201_CREATED,
        )
