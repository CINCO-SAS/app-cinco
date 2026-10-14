"""
Serializer de fechas límite de cierre (§5.8 / matriz B2, D2).

Contrato ADMCINCO (D-A3): valida forma; las reglas (unicidad del período)
viven en ParametrosService.
"""
from rest_framework import serializers

from ..models import FechaLimiteCierre


class FechaLimiteCierreSerializer(serializers.ModelSerializer):
    """Contrato de lectura/escritura de cierres.

    `modificado_por` (pk) y `modificado_en` emulan las columnas legacy
    `edit`/`fecha_edit` que devolvía get_all_fecha.
    """

    class Meta:
        model = FechaLimiteCierre
        fields = [
            "id",
            "mes",
            "anio",
            "fecha_limite",
            "modificado_por",
            "creado_en",
            "modificado_en",
        ]
        read_only_fields = ["id", "modificado_por", "creado_en", "modificado_en"]

    def validate_mes(self, value):
        if not 1 <= value <= 12:
            raise serializers.ValidationError("El mes debe estar entre 1 y 12.")
        return value

    def validate_anio(self, value):
        if not 2015 <= value <= 2100:
            raise serializers.ValidationError(
                "El año debe estar entre 2015 y 2100."
            )
        return value
