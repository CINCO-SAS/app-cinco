"""
FechaLimiteCierreViewSet — fechas límite de cierre (matriz B2 y D2).

Contrato ADMCINCO (D-A3): delega en ParametrosService y traduce sus
ValueError a HTTP 400/404.

Permisos (2026-10-26): el gate `DjangoModelPermissions` se sustituyó por
`PuedeVerModuloTransporte` — quien puede VER el módulo en su menú puede
operarlo. El gate de negocio `editar_tras_cierre` (§5.9) sigue activo en
el servicio.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import FechaLimiteCierre
from ..serializers import cierre_serializer
from ..services import ParametrosService
from .paginacion import PaginacionTransporte
from .permisos import PuedeVerModuloTransporte


class FechaLimiteCierreViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Abierto a quien puede ver el módulo en su menú (gate 2026-10-26)."""

    queryset = FechaLimiteCierre.objects.all()
    serializer_class = cierre_serializer.FechaLimiteCierreSerializer
    pagination_class = PaginacionTransporte
    permission_classes = [IsAuthenticatedOrAPIKey, PuedeVerModuloTransporte]

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        try:
            queryset = ParametrosService.listar_cierres(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            ParametrosService.obtener_cierre(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------ #
    # Escritura (D2 CRUD)
    # ------------------------------------------------------------------ #
    @extend_schema(request=cierre_serializer.FechaLimiteCierreSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cierre = ParametrosService.crear_cierre(
                serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            self.get_serializer(cierre).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=cierre_serializer.FechaLimiteCierreSerializer)
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        # obtener_cierre() fuera del try devolvía 500 (ValueError sin traducir)
        # en PATCH/PUT a un id inexistente; ahora responde 404 como retrieve.
        try:
            instance = ParametrosService.obtener_cierre(kwargs["pk"])
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        try:
            cierre = ParametrosService.actualizar_cierre(
                kwargs["pk"],
                serializer.validated_data,
                actor=self._actor(request),
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(self.get_serializer(cierre).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            ParametrosService.eliminar_cierre(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _actor(request):
        return getattr(request.user, "empleado", None)
