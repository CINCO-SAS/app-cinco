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

    # ------------------------------------------------------------------ #
    # Agregados de sábana (F5-7)
    # ------------------------------------------------------------------ #
    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description=(
            "Agregado 'día a día' de UNA fecha: áreas con desglose por "
            "carpetas (propios/renting/externos, total_dia) y contadores "
            "por estado (arr_estado: aprobado/validado/reportado/rechazado)."
        ),
    )
    @action(detail=False, methods=["get"], url_path="dia")
    def dia(self, request):
        serializer = informe_serializer.FechaSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        try:
            datos = InformeService.por_dia(serializer.validated_data["fecha"])
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"ok": True, "data": datos})

    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description=(
            "Agregado del mes por área con desglose por carpetas. "
            "solo_aprobados restringe los totales a APROBADO/VALIDADO "
            "(interruptor de la sábana)."
        ),
    )
    @action(detail=False, methods=["get"], url_path="area")
    def area(self, request):
        serializer = informe_serializer.PeriodoAprobadosSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            agregado = InformeService.por_area(
                datos["mes"], datos["anio"],
                solo_aprobados=datos["solo_aprobados"],
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"ok": True, "data": agregado})

    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description=(
            "Matriz área × meses del año: conteos e importes de salidas "
            "no eliminadas por (área, mes)."
        ),
    )
    @action(detail=False, methods=["get"], url_path="areas-mes")
    def areas_mes(self, request):
        serializer = informe_serializer.AnioSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        try:
            matriz = InformeService.areas_por_mes(serializer.validated_data["anio"])
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"ok": True, "data": matriz})

    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description=(
            "Agregado de nómina del mes: por (carpeta, placa) con días, "
            "valor base, retefuente 1 % y total a pagar. Excluye "
            "REPORTADO/ELIMINADO; pagador desde datos bancarios (servidor)."
        ),
    )
    @action(detail=False, methods=["get"], url_path="nomina")
    def nomina(self, request):
        serializer = informe_serializer.PeriodoSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            agregado = InformeService.nomina(datos["mes"], datos["anio"])
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"ok": True, "data": agregado})

    @extend_schema(
        auth=[{"sessionAuth": [], "apiKeyAuth": []}],
        responses={200: dict},
        description=(
            "Liquidación por placa del mes: días, valor base, retefuente "
            "1 %, pagar, pagador y consecutivo si ya existe. Excluye "
            "REPORTADO/ELIMINADO."
        ),
    )
    @action(detail=False, methods=["get"], url_path="liquidacion")
    def liquidacion(self, request):
        serializer = informe_serializer.PeriodoSerializer(
            data=request.query_params
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            agregado = InformeService.liquidacion_placa(
                datos["mes"], datos["anio"]
            )
        except ValueError as exc:
            return Response(
                {"ok": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"ok": True, "data": agregado})
