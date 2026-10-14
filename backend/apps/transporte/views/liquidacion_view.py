"""
LiquidacionViewSet — liquidaciones del Tab 3 (matriz D3 y D4).

Contrato ADMCINCO (D-A3): delega en LiquidacionService y traduce sus
ValueError a HTTP 400/403/404.

Rutas (decisión documentada): la matriz D3
`GET /liquidaciones/{anio}/{mes}/` se expresa como
`GET /liquidaciones/?mes=&anio=` — DefaultRouter reserva `/{pk}/` para el
detalle y los parámetros de consulta evitan la ambigüedad de ruta.

Permisos: lectura a autenticados; escrituras con DjangoModelPermissions
(queryset = PagoVehiculoMensual → add/change_pagovehiculomensual). El gate
de negocio de la fecha límite (permiso `transporte.editar_tras_cierre`) se
evalúa en las acciones de escritura; el afinado por acción llega con
PermisoService (E3).
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import PagoVehiculoMensual
from ..serializers import liquidacion_serializer
from ..services import LiquidacionService


class LiquidacionViewSet(ListModelMixin, GenericViewSet):
    """Lectura a autenticados; escritura con permiso de modelo + gate de cierre."""

    queryset = PagoVehiculoMensual.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey, DjangoModelPermissions]

    # ------------------------------------------------------------------ #
    # Consulta (D3)
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        try:
            queryset = LiquidacionService.listar_pagos(request.query_params)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    # ------------------------------------------------------------------ #
    # Sábanas (D4 / CR-10)
    # ------------------------------------------------------------------ #
    @extend_schema(
        responses={200: liquidacion_serializer.SabanaSerializer},
        description=(
            "Sábana de pago mensual: suma APROBADO + REPORTADO + VALIDADO (CR-10). "
            "Retrocede hasta 6 meses si el período pedido es el actual."
        ),
    )
    @action(detail=False, methods=["get"], url_path="pago-mensual")
    def pago_mensual(self, request):
        return self._responder_sabana(request, "sabana_pago_mensual")

    @extend_schema(
        responses={200: liquidacion_serializer.SabanaSerializer},
        description=(
            "Pronto pago: suma exclusivamente APROBADO (CR-10). "
            "Retrocede hasta 6 meses si el período pedido es el actual."
        ),
    )
    @action(detail=False, methods=["get"], url_path="pronto-pago")
    def pronto_pago(self, request):
        return self._responder_sabana(request, "sabana_pronto_pago")

    def _responder_sabana(self, request, metodo):
        filtros = {
            clave: request.query_params.get(clave)
            for clave in ("vehiculo", "placa", "conductor")
            if request.query_params.get(clave)
        }
        try:
            sabana = getattr(LiquidacionService, metodo)(
                request.query_params.get("mes"),
                request.query_params.get("anio"),
                filtros=filtros,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(liquidacion_serializer.SabanaSerializer(sabana).data)

    # ------------------------------------------------------------------ #
    # Escritura (con gate de fecha límite)
    # ------------------------------------------------------------------ #
    @extend_schema(request=liquidacion_serializer.ConsecutivoInputSerializer)
    @action(detail=False, methods=["post"], url_path="consecutivo")
    def consecutivo(self, request):
        serializer = liquidacion_serializer.ConsecutivoInputSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        periodo = serializer.validated_data

        rechazado = self._periodo_cerrado(request, periodo["mes"], periodo["anio"])
        if rechazado:
            return rechazado

        try:
            numero, creado = LiquidacionService.proximo_consecutivo(
                periodo["vehiculo"].pk,
                periodo["mes"],
                periodo["anio"],
                actor=self._actor(request),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        datos = {
            "vehiculo": numero.vehiculo_id,
            "mes": numero.mes,
            "anio": numero.anio,
            "consecutivo": numero.consecutivo,
            "creado": creado,
        }
        return Response(
            liquidacion_serializer.ConsecutivoSerializer(datos).data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )

    @extend_schema(request=liquidacion_serializer.PagoInputSerializer)
    @action(detail=False, methods=["post"], url_path="pago")
    def pago(self, request):
        serializer = liquidacion_serializer.PagoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        rechazado = self._periodo_cerrado(request, datos["mes"], datos["anio"])
        if rechazado:
            return rechazado

        try:
            pago = LiquidacionService.guardar_pago(
                datos, actor=self._actor(request)
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            liquidacion_serializer.PagoSerializer(pago).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------ #
    def _periodo_cerrado(self, request, mes, anio):
        """403 si el período pasó su fecha límite y el usuario no tiene
        `transporte.editar_tras_cierre` (§5.9 / B3)."""
        if LiquidacionService.puede_editar_periodo(
            mes,
            anio,
            tiene_permiso_editar=request.user.has_perm(
                "transporte.editar_tras_cierre"
            ),
        ):
            return None
        return Response(
            {
                "detail": (
                    f"El período {mes:02d}/{anio} está cerrado: requiere el "
                    "permiso transporte.editar_tras_cierre."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def _actor(request):
        return getattr(request.user, "empleado", None)
