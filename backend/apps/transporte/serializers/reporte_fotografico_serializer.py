"""
Serializadores del reporte fotográfico diario (F3/B3).

Contrato ADMCINCO (D-A3): validan forma (multipart + lista de imágenes); la
regla de negocio (ventana, agenda, duplicado) vive en ReporteFotograficoService.
"""
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from ..models import ReporteFotograficoVehiculo, ReporteFotoImagen
from ..services.reporte_fotografico_service import (
    MAX_BYTES_IMAGEN,
    MAX_IMAGENES,
    MSG_MAX_IMAGENES,
    MSG_MIN_IMAGENES,
)

# El legacy acepta jpeg/png/webp/gif/bmp/tiff/svg; el save re-codifica a JPEG.
TIPOS_IMAGEN_ACEPTADOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/svg+xml",
}


class CrearReporteFotoSerializer(serializers.Serializer):
    """Alta de reporte fotográfico (multipart). El responsable NO viene del cliente."""

    placa = serializers.CharField(max_length=10)
    imagenes = serializers.ListField(
        child=serializers.FileField(), allow_empty=False
    )
    ot_actividad = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    observaciones = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    # Georreferencia opcional del móvil (lat/lon/precisión/...).
    location = serializers.DictField(required=False, default=dict)

    def validate_imagenes(self, imagenes):
        imagenes = list(imagenes)
        if not imagenes:
            raise serializers.ValidationError(MSG_MIN_IMAGENES)
        if len(imagenes) > MAX_IMAGENES:
            raise serializers.ValidationError(MSG_MAX_IMAGENES)
        for imagen in imagenes:
            self._validar_archivo(imagen)
        return imagenes

    @staticmethod
    def _validar_archivo(imagen: UploadedFile) -> None:
        if not isinstance(imagen, UploadedFile):
            raise serializers.ValidationError("Archivo inválido.")
        contenido = getattr(imagen, "content_type", "") or ""
        if contenido and contenido not in TIPOS_IMAGEN_ACEPTADOS:
            raise serializers.ValidationError(
                f"Formato de imagen no admitido: {contenido}."
            )
        if imagen.size and imagen.size > MAX_BYTES_IMAGEN:
            raise serializers.ValidationError(
                f"Cada imagen no puede superar {MAX_BYTES_IMAGEN // (1024 * 1024)} MB."
            )


class ReporteFotoImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReporteFotoImagen
        fields = ["id", "imagen", "nombre_original"]


class ReporteFotograficoSerializer(serializers.ModelSerializer):
    imagenes = ReporteFotoImagenSerializer(many=True, read_only=True)
    placa = serializers.CharField(source="vehiculo.placa", read_only=True)
    responsable_cedula = serializers.CharField(
        source="responsable.cedula", read_only=True
    )
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ReporteFotograficoVehiculo
        fields = [
            "id",
            "placa",
            "fecha",
            "hora",
            "ot_actividad",
            "responsable_cedula",
            "responsable_nombre",
            "validacion_ot",
            "location",
            "observaciones",
            "imagenes",
            "creado_en",
        ]
        read_only_fields = fields

    def get_responsable_nombre(self, obj) -> str:
        empleado = obj.responsable
        return f"{empleado.nombre} {empleado.apellido}".strip()
