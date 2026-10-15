"""
Serializer de ValidacionSalida (cierre mensual por área, B4/F4).
"""
from rest_framework import serializers

from ..models import ValidacionSalida


class ValidacionSalidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidacionSalida
        fields = [
            "id",
            "area",
            "mes",
            "anio",
            "datos",
            "creado_en",
            "modificado_en",
        ]
        read_only_fields = ["creado_en", "modificado_en"]


class CerrarAreaSerializer(serializers.Serializer):
    """Escritura del cierre (mes/año del período + JSON `datos`)."""
    area = serializers.CharField()
    mes = serializers.IntegerField(min_value=1, max_value=12)
    anio = serializers.IntegerField(min_value=2015, max_value=2100)
    datos = serializers.DictField(required=False, default=dict)
