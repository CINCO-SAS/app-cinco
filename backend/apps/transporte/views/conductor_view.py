"""
ConductorViewSet — ABM del catálogo de conductores externos.

Contrato ADMCINCO (D-A3): delega en ConductorService; traduce sus
ValueError (mensaje en español) a HTTP 400, igual que el resto del repo.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Conductor
from ..serializers import conductor_serializer
from ..services import ConductorService


class ConductorViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Listado y detalle del catálogo de conductores + acciones de escritura
    (`crear`, `actualizar`, `inactivar`) validadas por el serializer.
    """

    queryset = Conductor.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ["cedula", "nombre_completo", "celular"]

    def get_serializer_class(self):
        if self.action == "list":
            return conductor_serializer.ConductorListSerializer
        return conductor_serializer.ConductorSerializer

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        try:
            queryset = ConductorService.listar(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            ConductorService.obtener(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return super().retrieve(request, *args, **kwargs)

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @extend_schema(request=conductor_serializer.ConductorSerializer)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conductor = ConductorService.crear(
                serializer.validated_data, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            conductor_serializer.ConductorSerializer(conductor).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=conductor_serializer.ConductorSerializer)
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parche = kwargs.pop("partial", False)
        try:
            conductor = ConductorService.actualizar(
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
        return Response(conductor_serializer.ConductorSerializer(conductor).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @extend_schema(
        request=None,
        responses={200: conductor_serializer.ConductorSerializer},
        description="Baja lógica; exige fecha_egreso (§5.4).",
    )
    @action(detail=True, methods=["post"], url_path="inactivar")
    def inactivar(self, request, pk=None):
        fecha_egreso = request.data.get("fecha_egreso")
        try:
            conductor = ConductorService.inactivar(
                pk, fecha_egreso, actor=self._actor(request)
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(conductor_serializer.ConductorSerializer(conductor).data)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _actor(request):
        """Empleado del token actual; None si la petición es anónima."""
        return getattr(request.user, "empleado", None)
