"""
KioscoViewSet — Endpoints unificados del kiosco de salidas (matriz S1–S4).

Contrato estandarizado ADMCINCO:
- Respuestas de éxito: { "ok": true, "data": ... }
- Respuestas de error: { "ok": false, "error": ... }

Endpoints consolidados:
- POST /kiosco/identificar/ (y alias /escanear/): resuelve placa o QR a vehículo + salida viva del día.
- POST /kiosco/validar/: pre-chequeo antes del alta (CR-9, registro APROBADO, duplicados CR-1/CR-2).
- GET  /kiosco/vehiculo/{placa}/: alias de consulta por URL directa.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..serializers import salida_serializer
from ..serializers.vehiculo_serializer import VehiculoSerializer
from ..services import FlotaService, SalidaService


class KioscoViewSet(GenericViewSet):
    """Flujos de interacción del kiosco de despacho vehicular."""

    permission_classes = [IsAuthenticatedOrAPIKey]

    # ------------------------------------------------------------------ #
    # Identificación consolidada (QR o Placa)
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=salida_serializer.IdentificarVehiculoSerializer,
        description="Resuelve la placa directa o el código QR a vehículo + salida viva de hoy.",
    )
    @action(detail=False, methods=["post"], url_path="identificar")
    def identificar(self, request):
        serializer = salida_serializer.IdentificarVehiculoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        placa = serializer.validated_data["placa"]
        return self._resolver_vehiculo_y_salida(placa)

    @action(detail=False, methods=["post"], url_path="escanear")
    def escanear(self, request):
        """Alias retrocompatible de /identificar/ para clientes de escáner QR."""
        return self.identificar(request)

    @action(detail=False, methods=["get"], url_path=r"vehiculo/(?P<placa>[^/.]+)")
    def vehiculo(self, request, placa=None):
        """Alias GET para consulta directa por placa en ruta."""
        return self._resolver_vehiculo_y_salida(placa)

    def _resolver_vehiculo_y_salida(self, placa):
        try:
            datos = FlotaService.vehiculo_por_placa(placa)
            salida = datos["salida"]
            return Response(
                {
                    "ok": True,
                    "data": {
                        "vehiculo": VehiculoSerializer(datos["vehiculo"]).data,
                        "salida": salida_serializer.SalidaSerializer(salida).data
                        if salida
                        else None,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ------------------------------------------------------------------ #
    # S3 — Pre-chequeo fecha/vehículo/móvil
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=salida_serializer.ValidarSerializer,
        responses={200: dict},
        description="S3: pre-chequeo antes del alta (CR-9, APROBADO, duplicados CR-1/CR-2).",
    )
    @action(detail=False, methods=["post"], url_path="validar")
    def validar(self, request):
        serializer = salida_serializer.ValidarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        try:
            res = SalidaService.pre_validar(
                datos["fecha"],
                datos["vehiculo"],
                datos.get("movil_sale", ""),
                usuario=request.user,
            )
            return Response(
                {
                    "ok": True,
                    "data": {
                        "validable": res["validable"],
                        "duplicado_vehiculo": res["duplicado_vehiculo"],
                        "duplicado_movil": res["duplicado_movil"],
                        "puede_registrar": res["puede_registrar"],
                        "mensaje": res["mensaje"],
                        "registro": salida_serializer.SalidaSerializer(res["registro"]).data
                        if res["registro"]
                        else None,
                        "salida": salida_serializer.SalidaSerializer(res["salida"]).data
                        if res["salida"]
                        else None,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
