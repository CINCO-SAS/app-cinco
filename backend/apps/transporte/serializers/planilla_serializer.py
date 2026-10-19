"""
Serializers de la Planilla Oficial de Salida (§5.6 / S5).

Contrato ADMCINCO (D-A3): validan forma; las reglas (CR-11, consecutivos,
filtro de alcance) viven en PlanillaService.
"""
from rest_framework import serializers



# Alcances válidos (espejo de PlanillaService.ALCANCES_VALIDOS).
ALCANCES_CHOICES = [
    ("PLACA", "Una placa específica"),
    ("TODAS", "Todas las placas activas"),
    ("PROPIO", "Todas las propias"),
    ("EXTERNO", "Todas las externas"),
    ("RENTING", "Todas las renting"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Input
# ─────────────────────────────────────────────────────────────────────────────

class PlanillaInputSerializer(serializers.Serializer):
    """POST /planillas/generar/ — parámetros de la planilla."""

    fecha = serializers.DateField(
        help_text="Fecha de la planilla (YYYY-MM-DD)."
    )
    alcance = serializers.ChoiceField(
        choices=ALCANCES_CHOICES,
        default="PLACA",
        help_text="Alcance de la planilla.",
    )
    placa = serializers.CharField(
        max_length=10,
        required=False,
        allow_blank=True,
        help_text="Placa del vehículo. Obligatoria si alcance='PLACA'.",
    )

    def validate(self, data):
        alcance = data.get("alcance", "PLACA").upper()
        placa = data.get("placa", "").strip()
        if alcance == "PLACA" and not placa:
            raise serializers.ValidationError(
                {"placa": "La placa es obligatoria cuando el alcance es 'PLACA'."}
            )
        if placa:
            data["placa"] = placa.upper()
        return data



# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

class SalidaDiaSerializer(serializers.Serializer):
    """Salida del día incluida en la planilla."""
    id = serializers.IntegerField()
    estado = serializers.CharField()
    conductor_cedula = serializers.CharField(allow_null=True)
    tecnico_cedula = serializers.CharField(allow_null=True)
    area = serializers.CharField(allow_null=True)
    carpeta = serializers.CharField(allow_null=True)
    observacion = serializers.CharField()


class ConductorPlanillaSerializer(serializers.Serializer):
    """Conductor habitual del vehículo (resumen para el formato físico)."""
    cedula = serializers.CharField()
    nombre = serializers.CharField()
    celular = serializers.CharField()
    licencia_categoria = serializers.CharField(allow_null=True)
    licencia_vencimiento = serializers.DateField(allow_null=True)


class VehiculoPlanillaSerializer(serializers.Serializer):
    """Fila de un vehículo en la planilla."""
    vehiculo_id = serializers.IntegerField()
    placa = serializers.CharField()
    tipo_vehiculo = serializers.CharField()
    tipo_contrato = serializers.CharField()
    marca = serializers.CharField()
    referencia = serializers.CharField(allow_null=True)
    modelo_anio = serializers.IntegerField()
    color = serializers.CharField(allow_null=True)
    nombre_propietario = serializers.CharField()
    cedula_propietario = serializers.CharField()
    conductor = ConductorPlanillaSerializer(allow_null=True)
    consecutivo = serializers.IntegerField()
    consecutivo_creado = serializers.BooleanField()
    mes = serializers.IntegerField()
    anio = serializers.IntegerField()
    ruta_qr = serializers.CharField(allow_null=True)
    salidas_del_dia = SalidaDiaSerializer(many=True)


class PlanillaSerializer(serializers.Serializer):
    """Respuesta completa de la Planilla Oficial de Salida."""
    fecha = serializers.DateField()
    alcance = serializers.CharField()
    vehiculos = VehiculoPlanillaSerializer(many=True)

