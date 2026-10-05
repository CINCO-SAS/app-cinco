from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.operaciones.serializers.agenda_serializer import (
    AgendaGuardarSerializer,
    AgendaImportarCsvSerializer,
    AgendaMesQuerySerializer,
    AgendaReadSerializer,
)
from apps.operaciones.services.agenda_service import AgendaService


class AgendaViewSet(viewsets.ViewSet):
    """
    ViewSet para la gestión completa del módulo de Agenda de Trabajos.
    Maneja la visualización mensual, autocompletado de OTs,
    administración de técnicos, agendamientos y eliminación lógica.
    """
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(
        summary="Consultar agendamientos de un mes o rango",
        description="Obtiene todos los registros de agendamiento para el mes, año y sede solicitados con datos de OT y ubicación.",
        parameters=[
            OpenApiParameter(name="mes", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False, description="Mes (01 a 12)"),
            OpenApiParameter(name="yyyy", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False, description="Año (ej. 2026)"),
            OpenApiParameter(name="sede", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False, description="Sede operativa"),
            OpenApiParameter(name="fecha_inicio", type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="fecha_fin", type=OpenApiTypes.DATE, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="responsable_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: AgendaReadSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="mes")
    def get_agendas_mes(self, request):
        serializer = AgendaMesQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        mes = serializer.validated_data.get("mes")
        yyyy = serializer.validated_data.get("yyyy")
        sede = serializer.validated_data.get("sede")
        fecha_inicio = serializer.validated_data.get("fecha_inicio")
        fecha_fin = serializer.validated_data.get("fecha_fin")
        responsable_id = serializer.validated_data.get("responsable_id")

        try:
            data = AgendaService.get_agendas_mes(
                mes=mes,
                yyyy=yyyy,
                sede=sede,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                responsable_id=responsable_id,
            )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "msg": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Guardar o actualizar un agendamiento",
        description="Crea o edita un agendamiento en `operaciones_agenda`.",
        request=AgendaGuardarSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["post"], url_path="guardar")
    def guardar_agenda(self, request):
        serializer = AgendaGuardarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "msg": "Datos inválidos", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resultado = AgendaService.save_agenda(
                data=serializer.validated_data,
                user=request.user,
            )
            return Response(resultado, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({"success": False, "msg": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "msg": f"Error al guardar la agenda: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Eliminar agendamiento (Soft-delete)",
        description="Marca como eliminado un agendamiento específico.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["delete"], url_path="eliminar")
    def eliminar_agenda(self, request, pk=None):
        try:
            res = AgendaService.eliminar_agenda(agenda_id=int(pk), user=request.user)
            return Response(res, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({"success": False, "msg": str(ve)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "msg": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Listar técnicos con agendamientos activos",
        description="Retorna el listado de técnicos que tienen agendamientos en el periodo reciente.",
        parameters=[
            OpenApiParameter(name="sede", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["get"], url_path="tecnicos-activos")
    def tecnicos_activos(self, request):
        sede = request.query_params.get("sede")
        try:
            tecnicos = AgendaService.get_tecnicos_activos(sede=sede)
            return Response(tecnicos, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "msg": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Buscar actividad por OT",
        description="Consulta los detalles de una OT para autocompletar nombre, ubicación y responsable en la agenda.",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["get"], url_path="actividad-ot/(?P<ot>[^/.]+)")
    def buscar_actividad_ot(self, request, ot=None):
        if not ot:
            return Response({"success": False, "msg": "OT no proporcionada."}, status=status.HTTP_400_BAD_REQUEST)

        data = AgendaService.buscar_actividad_por_ot(ot)
        if not data:
            return Response({"success": False, "msg": f"No se encontró la OT '{ot}'."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Importar archivo CSV de agendas",
        description="Procesa un archivo CSV para agendar masivamente en `operaciones_agenda`.",
        request=AgendaImportarCsvSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["post"], url_path="importar-csv")
    def importar_csv(self, request):
        serializer = AgendaImportarCsvSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = serializer.validated_data["file"]
        try:
            res = AgendaService.importar_csv(file_obj, user=request.user)
            return Response(res, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "msg": str(e)}, status=status.HTTP_400_BAD_REQUEST)
