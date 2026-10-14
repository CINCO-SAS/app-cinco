"""
JefeValidadorViewSet — jefes validadores por área/carpeta (matriz D1).

Contrato ADMCINCO (D-A3): delega en ParametrosService y traduce sus
ValueError a HTTP 400/404.

Permisos: la pantalla legacy de jefes (Tab 3) es de programación; aquí la
escritura queda bajo DjangoModelPermissions (`transporte.add/change_
jefevalidador`). El refinamiento a permisos granulares llega con E3.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import JefeValidador
from ..serializers import jefe_serializer
from ..services import ParametrosService


class JefeValidadorViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Lectura abierta a autenticados; escritura requiere permiso de modelo."""

    queryset = JefeValidador.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey, DjangoModelPermissions]

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        try:
            jefes = ParametrosService.listar_jefes(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(jefes)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            jefe = ParametrosService.obtener_jefe(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(self.get_serializer(jefe).data)

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @extend_schema(request=jefe_serializer.JefeValidadorSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            jefe = ParametrosService.crear_jefe(
                serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            jefe_serializer.JefeValidadorSerializer(jefe).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=jefe_serializer.JefeValidadorSerializer)
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kwargs.pop("partial", None)
        try:
            jefe = ParametrosService.actualizar_jefe(
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
        return Response(jefe_serializer.JefeValidadorSerializer(jefe).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    # ------------------------------------------------------------------ #
    # Acciones
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=None,
        responses={200: jefe_serializer.JefeValidadorSerializer},
        description="Baja lógica del jefe validador (nunca borrado físico).",
    )
    @action(detail=True, methods=["post"], url_path="inactivar")
    def inactivar(self, request, pk=None):
        try:
            jefe = ParametrosService.inactivar_jefe(
                pk, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(jefe_serializer.JefeValidadorSerializer(jefe).data)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _actor(request):
        return getattr(request.user, "empleado", None)
