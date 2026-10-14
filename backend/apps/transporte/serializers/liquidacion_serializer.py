"""
Serializers de liquidaciones (§5.2 / matriz D3, D4).

Contrato ADMCINCO (D-A3): validan forma; las reglas (CR-10, retroceso,
carrera de consecutivos) viven en LiquidacionService.
"""
from rest_framework import serializers

from ..models import PagoVehiculoMensual, Vehiculo
from ..models.choices import TipoPago


class ConsecutivoInputSerializer(serializers.Serializer):
    """POST /liquidaciones/consecutivo/ — genera o devuelve el número."""
    vehiculo = serializers.PrimaryKeyRelatedField(queryset=Vehiculo.objects.all())
    mes = serializers.IntegerField(min_value=1, max_value=12)
    anio = serializers.IntegerField(min_value=2015, max_value=2100)


class ConsecutivoSerializer(serializers.Serializer):
    vehiculo = serializers.IntegerField()
    mes = serializers.IntegerField()
    anio = serializers.IntegerField()
    consecutivo = serializers.IntegerField()
    creado = serializers.BooleanField()


class PagoInputSerializer(serializers.ModelSerializer):
    """POST /liquidaciones/pago/ — upsert de inscripción/marca de pago."""

    # Declarado a mano: sin default del model, para que si se omite NO aparezca
    # en validated_data y LiquidacionService calcule el snapshot (§5.1).
    total_liquidado = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, min_value=0
    )

    class Meta:
        model = PagoVehiculoMensual
        fields = ["vehiculo", "mes", "anio", "tipo", "pagado", "fecha_pago", "total_liquidado"]

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


class PagoSerializer(serializers.ModelSerializer):
    """GET /liquidaciones/ — fila del período (D3)."""
    placa = serializers.SerializerMethodField()

    class Meta:
        model = PagoVehiculoMensual
        fields = [
            "id", "vehiculo", "placa", "mes", "anio", "tipo",
            "pagado", "fecha_pago", "total_liquidado", "modificado_en",
        ]

    def get_placa(self, obj):
        return obj.vehiculo.placa


class SabanaFilaSerializer(serializers.Serializer):
    """Fila de sábana: columnas del legacy (322/395) + CR-10."""
    vehiculo = serializers.IntegerField()
    placa = serializers.CharField()
    tipo_contrato = serializers.CharField()
    conductor_cedula = serializers.CharField(allow_null=True)
    valor_dia = serializers.DecimalField(max_digits=12, decimal_places=2)
    dias = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    pagado = serializers.BooleanField()
    fecha_pago = serializers.DateField(allow_null=True)
    total_liquidado = serializers.DecimalField(max_digits=14, decimal_places=2)


class TotalesSerializer(serializers.Serializer):
    dias = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class SabanaSerializer(serializers.Serializer):
    """Respuesta de sábana: espeja mes/year + new_mes/new_yyyy del legacy."""
    mes = serializers.IntegerField()
    anio = serializers.IntegerField()
    mes_aplicado = serializers.IntegerField()
    anio_aplicado = serializers.IntegerField()
    retroactivo = serializers.BooleanField()
    filas = SabanaFilaSerializer(many=True)
    totales = TotalesSerializer()
