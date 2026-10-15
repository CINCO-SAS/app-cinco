"""
Serializers de Salidas (matriz S6/B1, §5.1).

- `SalidaSerializer`: salida a HTTP (lectura + payload de detalle).
- `RegistrarSalidaSerializer`: alta S6 — conserva los nombres legacy del
  form (`movil_sale`, `cc_asignada`) para que el contrato del kiosco y
  del backoffice sea reconocible frente a `transporte_salida.php`.
- `EscanearSerializer`: contenido crudo del QR escaneado (S1: el QR D-A8
  codifica la placa).
"""
from rest_framework import serializers

from ..models import Salida
from ..models.vehiculo import Vehiculo


class SalidaSerializer(serializers.ModelSerializer):
    vehiculo_placa = serializers.CharField(source="vehiculo.placa", read_only=True)
    total_a_pagar = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Salida
        fields = [
            "id",
            "vehiculo",
            "vehiculo_placa",
            "fecha_salida",
            "conductor",
            "tecnico_asignado",
            "es_disponible",
            "area",
            "carpeta",
            "sede",
            "valor_dia",
            "estado",
            "observacion",
            "reportado",
            "total_a_pagar",
            "creado_en",
        ]
        read_only_fields = [
            "estado",
            "reportado",
            "total_a_pagar",
            "creado_en",
        ]


class RegistrarSalidaSerializer(serializers.Serializer):
    fecha_salida = serializers.DateField()
    vehiculo = serializers.PrimaryKeyRelatedField(queryset=Vehiculo.objects.all())
    movil_sale = serializers.CharField(
        help_text="Cédula del personal que sale, o 'disponible'."
    )
    cc_asignada = serializers.CharField(required=False, allow_blank=True,
                                         default="")
    area = serializers.CharField(required=False, allow_blank=True, default="")
    carpeta = serializers.CharField(required=False, allow_blank=True, default="")
    sede = serializers.CharField(required=False, allow_blank=True, default="")
    observacion = serializers.CharField(required=False, allow_blank=True,
                                         default="")
    valor_dia = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0
    )

    def validate_movil_sale(self, valor):
        valor = (valor or "").strip()
        if not valor:
            raise serializers.ValidationError("movil_sale es requerido.")
        return valor


class EscanearSerializer(serializers.Serializer):
    contenido = serializers.CharField(
        help_text="Texto decodificado del QR (la placa del vehículo)."
    )
