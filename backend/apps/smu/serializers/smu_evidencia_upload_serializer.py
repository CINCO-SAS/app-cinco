"""Serializers de la subida de evidencias fotográficas (multipart)."""
from rest_framework import serializers

from apps.smu.models import SmuActividad, SmuActividadEvidencia
from apps.smu.services.smu_evidencia_service import (
    TOPE_FOTOS_POR_CAMPO,
    validar_archivo_foto,
)


class SmuEvidenciaUploadSerializer(serializers.Serializer):
    """Entrada de ``POST /smu/evidencias/`` (``multipart/form-data``)."""

    archivo = serializers.FileField(required=True)
    seccion = serializers.CharField(max_length=60)
    campo_origen = serializers.CharField(max_length=80, required=False,
                                         default='campo')
    actividad_id = serializers.IntegerField(required=False, allow_null=True,
                                            min_value=1)
    orden = serializers.IntegerField(required=False, allow_null=True,
                                     min_value=0, default=None)
    descripcion = serializers.CharField(required=False, allow_blank=True,
                                        allow_null=True, default='')

    def validate_archivo(self, archivo):
        # Valida magic bytes + 5 MB (ver `validar_archivo_foto`).
        error = validar_archivo_foto(archivo)
        if error:
            raise serializers.ValidationError(error)
        return archivo

    def validate_actividad_id(self, actividad_id):
        if actividad_id is None:
            return actividad_id
        if not SmuActividad.objects.filter(pk=actividad_id).exists():
            raise serializers.ValidationError(
                "No existe la actividad indicada."
            )
        return actividad_id

    def validate(self, attrs):
        """Tope del PHP (5 fotos por campo) cuando la actividad ya existe.

        En el flujo actual la foto se sube **al guardar** el formulario, o sea
        antes de crear la actividad: ahí no hay filas que contar y el tope lo
        fija ``SmuActividadSerializer`` sobre el payload de ``evidencias[]``.
        """
        actividad_id = attrs.get('actividad_id')
        campo = attrs.get('campo_origen') or 'campo'
        if actividad_id is not None:
            subidas = SmuActividadEvidencia.objects.filter(
                actividad_id=actividad_id,
                campo_origen=campo,
            ).count()
            if subidas >= TOPE_FOTOS_POR_CAMPO:
                raise serializers.ValidationError(
                    f"Máximo {TOPE_FOTOS_POR_CAMPO} fotos por campo: "
                    f"'{campo}' ya tiene {subidas}."
                )
        return attrs


class SmuEvidenciaUploadResponseSerializer(serializers.Serializer):
    """Salida de ``POST /smu/evidencias/``."""

    ruta_archivo = serializers.CharField(
        help_text="Ruta relativa a MEDIA_URL, para meterla en "
                  "`evidencias[].ruta_archivo` al crear la actividad."
    )
    url = serializers.CharField(help_text="URL para mostrar la foto en el navegador.")
    nombre = serializers.CharField(help_text="Nombre único generado en disco.")
    bytes = serializers.IntegerField(help_text="Tamaño del archivo guardado.")
