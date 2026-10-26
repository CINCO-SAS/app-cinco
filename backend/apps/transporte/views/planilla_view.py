"""
PlanillaViewSet — Planilla Oficial de Salida (§5.6 / S5).

Contrato ADMCINCO (D-A3) consolidado:
Endpoint único RPC-style para generar y consultar la planilla de despacho con QR y consecutivos.

Ruta registrada en urls.py:
  POST /planillas/generar/   → genera la planilla para el alcance y fecha dados.
  POST /planillas/formato/   → formato físico F-104 imprimible (HTML) — P1.

Respuesta estandarizada:
  Éxito: { "ok": true, "data": PlanillaPayload }
  Fallo: { "ok": false, "error": "mensaje descriptivo" }
"""
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..models import ConsecutivoMensual
from ..serializers import planilla_serializer
from ..services import PlanillaService
from .permisos import PuedeVerModuloTransporte


class PlanillaViewSet(GenericViewSet):
    """Genera la Planilla Oficial de Salida para uno o varios vehículos.

    Generar una planilla ESCRIBE (crea el ``ConsecutivoMensual`` que la
    respalda). Gate 2026-10-26: el ``DjangoModelPermissions`` se sustituyó
    por ``PuedeVerModuloTransporte`` — quien puede VER el módulo en su
    menú puede operarlo. Los controles de negocio del servicio
    (exclusión de motocicletas, ventana mensual, consecutivo atómico)
    siguen intactos.
    """

    queryset = ConsecutivoMensual.objects.all()
    permission_classes = [IsAuthenticatedOrAPIKey, PuedeVerModuloTransporte]

    @extend_schema(
        request=planilla_serializer.PlanillaInputSerializer,
        responses={200: planilla_serializer.PlanillaSerializer},
        description=(
            "Genera la Planilla Oficial de Salida consolidada (§5.6 / CR-11). "
            "Alcances: PLACA (una placa), PROPIO/EXTERNO/RENTING (por contrato), "
            "TODAS (toda la flota activa). "
            "Exclusión dura de motocicletas. "
            "El consecutivo mensual y el archivo QR se resuelven automáticamente."
        ),
    )
    @action(detail=False, methods=["post"], url_path="generar")
    def generar(self, request):
        serializer = planilla_serializer.PlanillaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        actor = getattr(request.user, "empleado", None)

        try:
            planilla = PlanillaService.generar_planilla(
                fecha=datos["fecha"],
                alcance=datos["alcance"],
                placa=datos.get("placa"),
                actor=actor,
            )
            return Response(
                {
                    "ok": True,
                    "data": planilla_serializer.PlanillaSerializer(planilla).data,
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ------------------------------------------------------------------ #
    # Formato físico F-104 (P1 — reemplaza planilla_salida.php)
    # ------------------------------------------------------------------ #
    @extend_schema(
        request=planilla_serializer.PlanillaInputSerializer,
        responses={200: None},
        description=(
            "Formato físico F-104 imprimible (P1): HTML autocontenido en "
            "LETTER horizontal, una hoja por vehículo, con QR embebido, "
            "consecutivo mensual y las casillas en blanco para firmas de "
            "salida/retorno. Recibe los mismos parámetros que "
            "/planillas/generar/ y genera los consecutivos igualmente."
        ),
    )
    @action(detail=False, methods=["post"], url_path="formato")
    def formato(self, request):
        serializer = planilla_serializer.PlanillaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data

        actor = getattr(request.user, "empleado", None)

        try:
            planilla = PlanillaService.generar_planilla(
                fecha=datos["fecha"],
                alcance=datos["alcance"],
                placa=datos.get("placa"),
                actor=actor,
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        html = PlanillaService.html_formato(planilla)
        return HttpResponse(html, content_type="text/html; charset=utf-8")
