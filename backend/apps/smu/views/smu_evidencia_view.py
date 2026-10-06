from rest_framework import mixins, parsers, status, viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.smu.serializers import (
    SmuEvidenciaUploadSerializer,
    SmuEvidenciaUploadResponseSerializer,
)
from apps.smu.services.smu_evidencia_service import guardar_evidencia


class SmuEvidenciaViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Subida de evidencias fotográficas — **solo** ``POST /smu/evidencias/``.

    Es el punto de entrada del binario del módulo SMU (A1): el formulario
    sube la foto al guardar, recibe ``ruta_archivo`` y esa ruta viaja dentro
    de ``evidencias[]`` cuando se crea la actividad.
    """

    serializer_class = SmuEvidenciaUploadSerializer
    parser_classes = [
        parsers.JSONParser,
        parsers.FormParser,
        parsers.MultiPartParser,
    ]

    @extend_schema(
        summary="Subir evidencia fotográfica",
        description=(
            "Guarda la foto en el servidor (validación por magic bytes, tope "
            "de 5 MB, nombre `uuid4` y conversión a WebP calidad 80, como el "
            "`saveFiles()` del PHP legado) y devuelve `ruta_archivo` para "
            "incluirlo en `evidencias[]` al crear la actividad. "
            "Recibe `multipart/form-data` con el campo `archivo`."
        ),
        request={"multipart/form-data": SmuEvidenciaUploadSerializer},
        responses={201: SmuEvidenciaUploadResponseSerializer},
        tags=["smu"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            datos = guardar_evidencia(
                archivo=serializer.validated_data['archivo'],
                seccion=serializer.validated_data['seccion'],
                campo_origen=(
                    serializer.validated_data.get('campo_origen') or 'campo'
                ),
                actividad_id=serializer.validated_data.get('actividad_id'),
                orden=serializer.validated_data.get('orden'),
                descripcion=serializer.validated_data.get('descripcion') or '',
            )
        except ValueError as e:
            # `guardar_evidencia` revalida por seguridad: si algo se coló,
            # es un problema del archivo y no un error del servidor.
            return Response(
                {"archivo": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(datos, status=status.HTTP_201_CREATED)
