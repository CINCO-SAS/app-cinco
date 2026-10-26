"""
DuenoViewSet — módulo «Dueños de vehículos» (2026-10-26).

Tabla de dueños, ficha completa (datos + vehículos + cuentas bancarias),
edición de los datos bancarios DEL DUEÑO y asignación de vehículos
existentes (1 dueño → N vehículos).

Permisos: gate `PuedeVerModuloTransporte` (quien ve el módulo en su
menú puede operarlo; 2026-10-26). Contrato ADMCINCO (D-A3): la vista
solo enruta y traduce los `ValueError` del servicio a HTTP 400/404.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import DuenoVehiculo
from ..serializers import dueno_serializer
from ..services import DuenoService
from .paginacion import PaginacionTransporte
from .permisos import PuedeVerModuloTransporte


class DuenoViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Abierto a quien puede ver el módulo en su menú (gate 2026-10-26)."""

    queryset = DuenoVehiculo.objects.all()
    serializer_class = dueno_serializer.DuenoResumenSerializer
    pagination_class = PaginacionTransporte
    permission_classes = [IsAuthenticatedOrAPIKey, PuedeVerModuloTransporte]

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        queryset = DuenoService.listar(request.query_params)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            dueno = DuenoService.obtener(kwargs["pk"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(dueno_serializer.DuenoSerializer(dueno).data)

    # ------------------------------------------------------------------ #
    # Escritura (datos del dueño)
    # ------------------------------------------------------------------ #
    @extend_schema(request=dueno_serializer.DuenoSerializer)
    def create(self, request, *args, **kwargs):
        serializer = dueno_serializer.DuenoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            dueno = DuenoService.crear(
                serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            dueno_serializer.DuenoSerializer(dueno).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=dueno_serializer.DuenoSerializer)
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = dueno_serializer.DuenoSerializer(
            data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        try:
            dueno = DuenoService.actualizar(
                kwargs["pk"], serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(dueno_serializer.DuenoSerializer(dueno).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            DuenoService.eliminar(kwargs["pk"])
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Vehículos del dueño (1 → N)
    # ------------------------------------------------------------------ #
    @extend_schema(request=dueno_serializer.AsignarVehiculoSerializer)
    @action(detail=True, methods=["post"], url_path="vehiculos")
    def asignar_vehiculo(self, request, pk=None):
        serializer = dueno_serializer.AsignarVehiculoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            vehiculo = DuenoService.asignar_vehiculo(
                pk, serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(
            dueno_serializer.VehiculoDelDuenoSerializer(vehiculo).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"vehiculos/(?P<vehiculo_id>[^/.]+)",
    )
    def quitar_vehiculo(self, request, pk=None, vehiculo_id=None):
        try:
            DuenoService.quitar_vehiculo(
                pk, vehiculo_id, actor=self._actor(request)
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Cuentas bancarias del dueño
    # ------------------------------------------------------------------ #
    @extend_schema(request=dueno_serializer.GuardarBancariosSerializer)
    @action(detail=True, methods=["put", "patch"], url_path="bancarios")
    def bancarios(self, request, pk=None):
        serializer = dueno_serializer.GuardarBancariosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cuentas = DuenoService.guardar_bancarios(
                pk,
                serializer.validated_data["cuentas"],
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
            dueno_serializer.DatosBancariosDuenoSerializer(cuentas, many=True).data
        )

    # ------------------------------------------------------------------ #
    @staticmethod
    def _actor(request):
        return getattr(request.user, "empleado", None)
