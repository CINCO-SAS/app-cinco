"""
LiquidacionViewSet — Liquidaciones del Tab 3 (matriz D3 y D4).

Contrato ADMCINCO (D-A3) consolidado:
- Respuestas estandarizadas:
    Éxito: { "ok": true, "data": ... }
    Fallo: { "ok": false, "error": ..., "detail": ... }

Rutas consolidadas:
- GET  /liquidaciones/?mes=&anio=          → lista pagos registrados en el período.
- GET  /liquidaciones/sabana/               → sábana consolidada (?tipo=pago-mensual|pronto-pago).
- GET  /liquidaciones/pago-mensual/         → alias retrocompatible.
- GET  /liquidaciones/pronto-pago/          → alias retrocompatible.
- POST /liquidaciones/consecutivo/          → genera o consulta consecutivo atómico mensual.
- POST /liquidaciones/pago/                 → upsert de marca de pago mensual.
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
from .paginacion import PaginacionTransporte


class LiquidacionViewSet(ListModelMixin, GenericViewSet):
    """Lectura a autenticados; escritura con permiso de modelo + gate de cierre."""

    queryset = PagoVehiculoMensual.objects.all()
    pagination_class = PaginacionTransporte
    serializer_class = liquidacion_serializer.PagoSerializer
    permission_classes = [IsAuthenticatedOrAPIKey, DjangoModelPermissions]

    # ------------------------------------------------------------------ #
    # Consulta (D3)
    # ------------------------------------------------------------------ #
    def list(self, request, *args, **kwargs):
        try:
            queryset = LiquidacionService.listar_pagos(request.query_params)
        except ValueError as exc:
            return self._error(exc)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    # ------------------------------------------------------------------ #
    # Sábanas (D4 / CR-10) — Consolidado con aliases
    # ------------------------------------------------------------------ #
    @extend_schema(
        responses={200: liquidacion_serializer.SabanaSerializer},
        description="Sábana consolidada de liquidación. Parámetro tipo=pago-mensual | pronto-pago.",
    )
    @action(detail=False, methods=["get"], url_path="sabana")
    def sabana(self, request):
        tipo = request.query_params.get("tipo", "pago-mensual").lower()
        metodo = (
            "sabana_pronto_pago"
            if tipo in ("pronto-pago", "pronto_pago")
            else "sabana_pago_mensual"
        )
        return self._responder_sabana(request, metodo)

    @action(detail=False, methods=["get"], url_path="pago-mensual")
    def pago_mensual(self, request):
        """Alias retrocompatible de /sabana/?tipo=pago-mensual."""
        return self._responder_sabana(request, "sabana_pago_mensual")

    @action(detail=False, methods=["get"], url_path="pronto-pago")
    def pronto_pago(self, request):
        """Alias retrocompatible de /sabana/?tipo=pronto-pago."""
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
            return Response(
                {
                    "ok": True,
                    "data": liquidacion_serializer.SabanaSerializer(sabana).data,
                }
            )
        except ValueError as exc:
            return self._error(exc)

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
            datos = {
                "vehiculo": numero.vehiculo_id,
                "mes": numero.mes,
                "anio": numero.anio,
                "consecutivo": numero.consecutivo,
                "creado": creado,
            }
            return Response(
                {
                    "ok": True,
                    "data": liquidacion_serializer.ConsecutivoSerializer(datos).data,
                },
                status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
            )
        except ValueError as exc:
            return self._error(exc)

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
            return Response(
                {
                    "ok": True,
                    "data": liquidacion_serializer.PagoSerializer(pago).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return self._error(exc)

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

        mensaje = (
            f"El período {mes:02d}/{anio} está cerrado: requiere el "
            "permiso transporte.editar_tras_cierre."
        )
        return Response(
            {"ok": False, "error": mensaje, "detail": mensaje},
            status=status.HTTP_403_FORBIDDEN,
        )

    @staticmethod
    def _error(exc):
        codigo = (
            status.HTTP_404_NOT_FOUND
            if "No existe" in str(exc)
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(
            {"ok": False, "error": str(exc), "detail": str(exc)},
            status=codigo,
        )

    @staticmethod
    def _actor(request):
        return getattr(request.user, "empleado", None)
