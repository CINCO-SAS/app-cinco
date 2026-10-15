"""
SalidaViewSet — alta, consulta y backoffice de salidas (matriz S6 + B1
+ B4/F4).

Contrato ADMCINCO (D-A3): delega en SalidaService y traduce sus
ValueError a HTTP 400/404.

Endpoints:
- `POST /salidas/` (S6): alta con ventana CR-9, anticolisión CR-1/CR-2 y
  exigencia de personal — todo en el servicio.
- `GET /salidas/?desde=&hasta=&estado=&...` (B1): filtros server-side.
- `GET /salidas/{id}/`: detalle con snapshots.
- `POST /salidas/aprobar-lote/` (B12): aprobación masiva atómica.
- `POST /salidas/{id}/rechazar/` (B13): motivo obligatorio.
- `POST /salidas/{id}/validar/` (D-A11): APROBADO → VALIDADO.
- `DELETE /salidas/{id}/` (B5): borrado lógico con ventana CR-9.
- `POST|DELETE /salidas/{id}/novedad/` (B6/B7): UNA novedad por salida.
- `GET /salidas/{id}/historial/` (B4): filas de SalidaHistorial.

Permisos: lectura a autenticados; la alta exige `transporte.add_salida`
(DjangoModelPermissions); las acciones de backoffice exigen
`transporte.change_salida` (`_PermisosGestionSalida`), y el borrado
`transporte.delete_salida`. El control por FILA (jefe del área/carpeta,
CR-9) lo hace el servicio y se expone en el serializer (B15).
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import Salida
from ..serializers import salida_serializer
from ..services import SalidaService
from .paginacion import PaginacionTransporte


class _PermisosGestionSalida(DjangoModelPermissions):
    """
    Acciones de backoffice (aprobar-lote, rechazar, validar, novedad):
    no son un alta, sino la gestión de filas existentes ⇒ `change_salida`.
    DRF expone el mapa como `perms_map` (atributo público de la clase).
    """

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "POST": ["%(app_label)s.change_%(model_name)s"],
    }


class SalidaViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """Lectura a autenticados; escritura con permisos de modelo (E3
    refinará a permisos granulares por funcionalidad)."""

    queryset = Salida.objects.all()
    serializer_class = salida_serializer.SalidaSerializer
    permission_classes = [IsAuthenticatedOrAPIKey, DjangoModelPermissions]
    # Sin paginación declarada `get_paginated_response` daba 500 (ver
    # views/paginacion.py); ahora /salidas/ pagina de verdad.
    pagination_class = PaginacionTransporte

    def get_permissions(self):
        if self.action in (
            "aprobar_lote", "aprobar", "rechazar", "validar", "novedad"
        ):
            # Mantiene la autenticación (IsAuthenticatedOrAPIKey) y solo
            # sustituye el permiso de modelo por el de gestión (change).
            return [
                perm() for perm in self.permission_classes
                if perm is not DjangoModelPermissions
            ] + [_PermisosGestionSalida()]
        return super().get_permissions()

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
            salida_serializer.SalidaSerializer(
                salida, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """B5: borrado lógico (ELIMINADO) con ventana CR-9."""
        try:
            SalidaService.eliminar(kwargs["pk"], usuario=request.user)
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------ #
    # Backoffice B4 (F4)
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=salida_serializer.AprobarLoteSerializer,
        responses={200: salida_serializer.SalidaSerializer(many=True)},
        description="B12: aprobación masiva (todas o ninguna).",
    )
    @action(detail=False, methods=["post"], url_path="aprobar-lote")
    def aprobar_lote(self, request, *args, **kwargs):
        serializer = salida_serializer.AprobarLoteSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        try:
            salidas = SalidaService.aprobar_masivo(
                serializer.validated_data["ids"], usuario=request.user
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            salida_serializer.SalidaSerializer(
                salidas, many=True, context=self.get_serializer_context()
            ).data
        )

    @extend_schema(
        request=None,
        responses={200: salida_serializer.SalidaSerializer},
        description="D-A11: REPORTADO → APROBADO.",
    )
    @action(detail=True, methods=["post"], url_path="aprobar")
    def aprobar(self, request, pk=None):
        return self._transicion(request, SalidaService.aprobar)

    @extend_schema(
        request=salida_serializer.RechazarSerializer,
        responses={200: salida_serializer.SalidaSerializer},
        description="B13: RECHAZADO con motivo obligatorio.",
    )
    @action(detail=True, methods=["post"], url_path="rechazar")
    def rechazar(self, request, *args, **kwargs):
        serializer = salida_serializer.RechazarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._transicion(
            request,
            lambda salida_id, usuario: SalidaService.rechazar(
                salida_id, serializer.validated_data["motivo"],
                usuario=usuario,
            ),
        )

    @extend_schema(
        request=None,
        responses={200: salida_serializer.SalidaSerializer},
        description="D-A11: APROBADO → VALIDADO.",
    )
    @action(detail=True, methods=["post"], url_path="validar")
    def validar(self, request, *args, **kwargs):
        return self._transicion(request, SalidaService.validar)

    @extend_schema(
        request=salida_serializer.NovedadSerializer,
        responses={200: salida_serializer.SalidaSerializer},
        description="B6: reportar novedad (UNA por salida, sobrescribe).",
    )
    @extend_schema(
        methods=["DELETE"],
        request=None,
        responses={204: None},
        description="B7: eliminar novedad (limpia con auditoría).",
    )
    @action(detail=True, methods=["post", "delete"], url_path="novedad")
    def novedad(self, request, *args, **kwargs):
        if request.method == "DELETE":
            try:
                SalidaService.eliminar_novedad(
                    kwargs["pk"], usuario=request.user
                )
            except ValueError as exc:
                codigo = (
                    status.HTTP_404_NOT_FOUND
                    if "No existe" in str(exc)
                    else status.HTTP_400_BAD_REQUEST
                )
                return Response({"detail": str(exc)}, status=codigo)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = salida_serializer.NovedadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            SalidaService.registrar_novedad(
                kwargs["pk"],
                serializer.validated_data["tipo"],
                serializer.validated_data["valor"],
                serializer.validated_data["descripcion"],
                usuario=request.user,
            )
        except ValueError as exc:
            codigo = (
                status.HTTP_404_NOT_FOUND
                if "No existe" in str(exc)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": str(exc)}, status=codigo)
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(
        responses={200: salida_serializer.HistorialSerializer(many=True)},
        description="B4: historial de estados (filas, no JSON).",
    )
    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, *args, **kwargs):
        try:
            filas = SalidaService.historial(kwargs["pk"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        page = self.paginate_queryset(filas)
        serializer = salida_serializer.HistorialSerializer(
            page, many=True
        )
        return self.get_paginated_response(serializer.data)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _error(exc):
        codigo = (
            status.HTTP_404_NOT_FOUND
            if "No existe" in str(exc)
            else status.HTTP_400_BAD_REQUEST
        )
        return Response({"detail": str(exc)}, status=codigo)

    def _transicion(self, request, metodo, *args):
        try:
            salida = metodo(self.kwargs["pk"], *args, usuario=request.user)
        except ValueError as exc:
            return self._error(exc)
        return Response(
            salida_serializer.SalidaSerializer(
                salida, context=self.get_serializer_context()
            ).data
        )
