"""
InformeViewSet — Tab 2 Informes (matriz I1, §5.7).

Contrato ADMCINCO (D-A3): delega en InformeService y traduce sus
ValueError a HTTP 400.

F5-1: `GET /informes/cuenta-cobro/?placa=&mes=&anio=` devuelve la cuenta
de cobro como `text/html` imprimible (el navegador la abre en pestaña
nueva e imprime a PDF), reemplazando `cuenta_cobro_plantilla.php`.

Sólo lectura a autenticados (como el resto de sábanas): no escribe BD.
"""
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.security.permissions.api_permissions import IsAuthenticatedOrAPIKey

from ..serializers import informe_serializer, salida_serializer
from ..services import InformeService
from .paginacion import PaginacionTransporte


class InformeViewSet(GenericViewSet):
    """InformeService: solo lectura de sábanas (Tab 2)."""

    permission_classes = [IsAuthenticatedOrAPIKey]
    pagination_class = PaginacionTransporte

    # ------------------------------------------------------------------ #
    # Cuenta de cobro (F5-1)
    # ------------------------------------------------------------------ #
    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: None},
        description=(
            "Cuenta de cobro imprimible del alquiler del vehículo para el "
            "periodo dado (HTML). El importe y el pagador se calculan en el "
            "servidor desde las salidas del mes."
        ),
    )
    @action(detail=False, methods=["get"], url_path="cuenta-cobro")
    def cuenta_cobro(self, request):
        serializer = informe_serializer.CuentaCobroSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            cuenta = InformeService.cuenta_cobro(
                datos["placa"], datos["mes"], datos["anio"]
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        html = InformeService.html_cuenta_cobro(cuenta)
        return HttpResponse(html, content_type="text/html; charset=utf-8")

    # ------------------------------------------------------------------ #
    # Serie del gráfico por área (F5-2)
    # ------------------------------------------------------------------ #
    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description=(
            "Series del gráfico 'Pagos por Mes, por Área' de la sábana: "
            "suma de total_a_pagar por (área, mes). I&M va al eje "
            "secundario. Año opcional."
        ),
    )
    @action(detail=False, methods=["get"], url_path="series-chart")
    def series_chart(self, request):
        serializer = informe_serializer.SeriesChartSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        serie = InformeService.series_chart(serializer.validated_data.get("anio"))
        return Response({"ok": True, "data": serie})

    # ------------------------------------------------------------------ #
    # Informe mensual de salidas (F5-3, §5.7)
    # ------------------------------------------------------------------ #
    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: salida_serializer.SalidaSerializer(many=True)},
        description=(
            "Informe mensual (día a día) de salidas no eliminadas del "
            "periodo, con filtros estado/sede/área/carpeta/search "
            "server-side. Paginado."
        ),
    )
    @action(detail=False, methods=["get"], url_path="mensual")
    def mensual(self, request):
        serializer = informe_serializer.InformeMensualSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        filtros = {
            clave: datos[clave]
            for clave in ("estado", "sede", "area", "carpeta", "search")
        }
        queryset = InformeService.mensual(datos["mes"], datos["anio"], filtros)
        page = self.paginate_queryset(queryset)
        serializador = salida_serializer.SalidaSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializador.data)

    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description="Áreas presentes en el periodo (para poblar el filtro).",
    )
    @action(detail=False, methods=["get"], url_path="areas")
    def areas(self, request):
        serializer = informe_serializer.PeriodoSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        return Response(
            {
                "ok": True,
                "data": {
                    "areas": InformeService.areas_del_periodo(
                        datos["mes"], datos["anio"]
                    )
                },
            }
        )
