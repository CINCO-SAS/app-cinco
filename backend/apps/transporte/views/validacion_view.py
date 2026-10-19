"""
ValidacionViewSet — cierre mensual de validación de salidas por área
(B4/F4, legacy `get_valid_trans`).

Contrato ADMCINCO (D-A3): delega en ValidacionService y traduce sus
ValueError a HTTP 400/404.

Endpoints:
- `GET /validaciones/?mes=&anio=&area=`: consulta (reemplaza
  `get_valid_trans`).
- `POST /validaciones/`: upert del cierre del área; exige jefe
  validador del área (A1) o programación/admin — el control de rol lo
  hace el servicio (B15).
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import ValidacionSalida
from ..serializers import validacion_serializer
from ..services import ValidacionService
from .paginacion import PaginacionTransporte


class ValidacionViewSet(ListModelMixin, GenericViewSet):
    """Lectura a autenticados; escritura con permiso de modelo (E3
    refinará a permisos granulares); el rol de jefe del área lo valida
    el servicio."""

    queryset = ValidacionSalida.objects.all()
    pagination_class = PaginacionTransporte
    serializer_class = validacion_serializer.ValidacionSalidaSerializer
    permission_classes = [IsAuthenticatedOrAPIKey, DjangoModelPermissions]

    def list(self, request, *args, **kwargs):
        try:
            validaciones = ValidacionService.listar(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(validaciones)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=validacion_serializer.CerrarAreaSerializer,
        responses={200: validacion_serializer.ValidacionSalidaSerializer},
        description="Cierra (o reabre con nuevos datos) el mes de un "
                    "área. Jefe del área o programación.",
    )
    def create(self, request, *args, **kwargs):
        serializer = validacion_serializer.CerrarAreaSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        try:
            validacion = ValidacionService.cerrar_area(
                serializer.validated_data, usuario=request.user
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_403_FORBIDDEN
                if "permisos" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(
            validacion_serializer.ValidacionSalidaSerializer(validacion).data,
            status=status.HTTP_201_CREATED,
        )
