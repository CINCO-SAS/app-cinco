"""
KioscoViewSet — endpoints del kiosco de salidas (matriz S1–S4).

S1 `POST /kiosco/escanear/`: la cámara/escáner del kiosco decodifica el
QR (D-A8: codifica la placa) y envía el texto crudo; el backend resuelve
vehículo + salida del día (FlotaService.escanear). Escaneo = lectura
operativa: autenticación (usuario o API key del kiosco) — el permiso de
modelo (`add_salida`) aplica al ALTA en /salidas/ (S6), no aquí.

S2/S3/S4 (`asignar-movil`, `validar`, `vehiculo/{placa}/`) llegan en
siguientes entregas del Tramo B.
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..serializers import salida_serializer
from ..serializers.vehiculo_serializer import VehiculoSerializer
from ..services import FlotaService


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
