"""
Serializers de informes (Tab 2) — F5.

- `CuentaCobroSerializer`: entrada mínima de la cuenta de cobro (F5-1).
  Deliberadamente SOLO placa + periodo: el importe y el pagador se
  calculan/leen en el servidor (ver `InformeService`), a diferencia del
  legacy que los recibía en campos ocultos del formulario.
"""
from rest_framework import serializers


class CuentaCobroSerializer(serializers.Serializer):
    """Entrada F5-1: placa + periodo de la cuenta de cobro."""

    placa = serializers.CharField(max_length=20)
    mes = serializers.IntegerField(min_value=1, max_value=12)
    anio = serializers.IntegerField(min_value=2000, max_value=2100)

    def validate_placa(self, valor):
        valor = (valor or "").strip().upper()
        if not valor:
            raise serializers.ValidationError("Debe indicar la placa.")
        return valor


class SeriesChartSerializer(serializers.Serializer):
    """Entrada F5-2: año opcional para acotar el gráfico por área."""

    anio = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        min_value=2000,
        max_value=2100,
        help_text="Sin año se grafica todo el histórico.",
    )
