"""
KioscoViewSet — endpoints del kiosco de salidas (matriz S1–S4).

S1 `POST /kiosco/escanear/`: la cámara/escáner del kiosco decodifica el
QR (D-A8: codifica la placa) y envía el texto crudo; el backend resuelve
vehículo + salida del día (FlotaService.escanear). Escaneo = lectura
operativa: autenticación (usuario o API key del kiosco) — el permiso de
modelo (`add_salida`) aplica al ALTA en /salidas/ (S6), no aquí.

S3 `POST /kiosco/validar/`: pre-chequeo de solo lectura (CR-9, CR-1, CR-2)
antes del alta S6 (SalidaService.pre_validar).
S4 `GET /kiosco/vehiculo/{placa}/`: consulta por placa + estado de la salida
del día (FlotaService.vehiculo_por_placa).

S2 (`asignar-movil`, outbox hacia Nokia) espera la decisión D-A9 (gate G4).
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
    permission_classes = [IsAuthenticatedOrAPIKey]

    @extend_schema(
        request=salida_serializer.EscanearSerializer,
        description="Resuelve el QR escaneado (placa) a vehículo + salida "
                    "de hoy.",
    )
    @action(detail=False, methods=["post"], url_path="escanear")
    def escanear(self, request):
        serializer = salida_serializer.EscanearSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            datos = FlotaService.escanear(serializer.validated_data["contenido"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        salida = datos["salida"]
        return Response(
            {
                "vehiculo": VehiculoSerializer(datos["vehiculo"]).data,
                "salida": salida_serializer.SalidaSerializer(salida).data
                if salida
                else None,
            }
        )

    # ------------------------------------------------------------------ #
    # S3 — pre-chequeo fecha/vehículo/móvil (solo lectura)
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=salida_serializer.ValidarSerializer,
        responses={200: dict},
        description="S3: pre-chequeo antes del alta (S6): CR-9, registro "
                    "APROBADO del vehículo, y duplicados CR-1/CR-2.",
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
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {
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
            }
        )

    # ------------------------------------------------------------------ #
    # S4 — consulta por placa + estado del día
    # ------------------------------------------------------------------ #
    @extend_schema(
        responses={200: dict},
        description="S4: consulta por placa y estado de la salida del día.",
    )
    @action(
        detail=False,
        methods=["get"],
        url_path=r"vehiculo/(?P<placa>[^/.]+)",
    )
    def vehiculo(self, request, placa=None):
        try:
            datos = FlotaService.vehiculo_por_placa(placa)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        salida = datos["salida"]
        return Response(
            {
                "vehiculo": VehiculoSerializer(datos["vehiculo"]).data,
                "salida": salida_serializer.SalidaSerializer(salida).data
                if salida
                else None,
            }
        )
