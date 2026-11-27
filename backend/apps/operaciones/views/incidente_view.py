from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.operaciones.serializers.incidente_serializer import (
    IncidenteBuscarQuerySerializer,
)
from apps.operaciones.services.incidente_sharepoint_service import (
    IncidenteConfigError,
    IncidenteSharePointError,
    IncidenteSharePointService,
)


class IncidenteViewSet(viewsets.ViewSet):
    """
    ViewSet para consultar incidentes desde archivos Excel alojados en SharePoint.
    """

    @extend_schema(
        summary="Listar fuentes de incidentes disponibles",
        description="Retorna los archivos configurados en SharePoint para poblar el selector en la vista de Incidentes.",
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=["get"], url_path="fuentes")
    def listar_fuentes(self, request):
        fuentes = IncidenteSharePointService.listar_fuentes()
        return Response(
            {
                "success": True,
                "fuentes": fuentes,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Consultar incidente por INC en SharePoint",
        description="Busca un INC en la fuente de Excel seleccionada y retorna F_CREACION, OT, CLIENTE y ESTADO.",
        parameters=[
            OpenApiParameter(
                name="inc",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Código del incidente (ej: INC000007572996)",
            ),
            OpenApiParameter(
                name="fuente",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Clave de la fuente configurada (por defecto la primera habilitada)",
            ),
            OpenApiParameter(
                name="refresh",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Forzar actualización desde SharePoint (sujeto a cooldown)",
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=False, methods=["get"], url_path="buscar")
    def buscar(self, request):
        serializer = IncidenteBuscarQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))[0]
            return Response(
                {
                    "success": False,
                    "detail": str(first_error),
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        inc = serializer.validated_data["inc"]
        fuente = serializer.validated_data.get("fuente") or None
        refresh = serializer.validated_data.get("refresh", False)

        try:
            resultado = IncidenteSharePointService.buscar_incidente(
                inc=inc,
                fuente=fuente,
                refresh=refresh,
            )
        except IncidenteConfigError as exc:
            return Response(
                {"success": False, "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IncidenteSharePointError as exc:
            return Response(
                {"success": False, "detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not resultado["encontrado"]:
            return Response(
                {
                    "success": False,
                    "detail": (
                        f"No se encontró el incidente '{resultado['inc']}' "
                        f"en '{resultado['fuente']['label']}'."
                    ),
                    **resultado,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                **resultado,
            },
            status=status.HTTP_200_OK,
        )
