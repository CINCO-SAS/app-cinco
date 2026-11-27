import re
from rest_framework import serializers


class IncidenteBuscarQuerySerializer(serializers.Serializer):
    """Valida y normaliza los parámetros de consulta de un incidente en SharePoint."""

    INC_PATTERN = re.compile(r"^[A-Z0-9_-]+$")

    inc = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=40,
        trim_whitespace=True,
        error_messages={
            "required": "Debes ingresar el código del incidente (INC).",
            "blank": "Debes ingresar el código del incidente (INC).",
            "max_length": "El código de incidente no puede superar 40 caracteres.",
        },
    )
    fuente = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        trim_whitespace=True,
    )
    refresh = serializers.BooleanField(required=False, default=False)

    def validate_inc(self, value: str) -> str:
        clean = (value or "").strip().upper()
        if not clean:
            raise serializers.ValidationError("Debes ingresar el código del incidente (INC).")
        if not self.INC_PATTERN.fullmatch(clean):
            raise serializers.ValidationError(
                "El código INC solo puede contener letras, números, guiones (-) o guiones bajos (_)."
            )
        return clean

    def validate_fuente(self, value: str) -> str:
        return (value or "").strip()
