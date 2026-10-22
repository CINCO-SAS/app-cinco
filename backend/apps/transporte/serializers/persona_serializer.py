"""
Serializers de la ficha de personas/móviles (B9).

Documenta la forma de `GET /personas/{cedula}/ficha-movil/` en el esquema
OpenAPI. Los valores los calcula el servicio; aquí no hay lógica.

`origen` dice en qué escalón de la cascada se resolvió la cédula:
  · `conductor_externo` — `transporte_base_conductores` → `Conductor`
  · `personal`          — `cinco_base_de_personal` → `Empleado` (BD azul)
  · `null`              — no se encontró; solo la línea corporativa podría
                          resolverla, y esa está tras el gate G4/D-A10
"""
from rest_framework import serializers


class VehiculoFichaSerializer(serializers.Serializer):
    """Vehículo asignado o vehículo con el que salió (datos mínimos)."""

    id = serializers.IntegerField()
    placa = serializers.CharField()
    marca = serializers.CharField(allow_null=True, required=False)
    referencia = serializers.CharField(allow_null=True, required=False)
    tipo_vehiculo = serializers.CharField(allow_null=True, required=False)
    ciudad_operacion = serializers.CharField(allow_null=True, required=False)


class SalidaHoySerializer(serializers.Serializer):
    """Salida viva de HOY del móvil."""

    id = serializers.IntegerField()
    fecha_salida = serializers.CharField()
    estado = serializers.CharField()
    area = serializers.CharField(allow_null=True, required=False)
    carpeta = serializers.CharField(allow_null=True, required=False)
    sede = serializers.CharField(allow_null=True, required=False)
    valor_dia = serializers.CharField(
        help_text="Tarifa del día ya redondeada a 2 decimales, en texto."
    )
    es_disponible = serializers.BooleanField(
        help_text="True si la salida fue por el vehículo 'disponible'."
    )
    reportado = serializers.BooleanField()


class FichaMovilSerializer(serializers.Serializer):
    """Ficha del móvil (B9 · §5.1)."""

    cedula = serializers.CharField()
    origen = serializers.CharField(
        allow_null=True,
        required=False,
        help_text=(
            "conductor_externo | personal | null. Dice en qué escalón de la "
            "cascada se resolvió la cédula."
        ),
    )
    nombre = serializers.CharField(allow_null=True, required=False)
    area = serializers.CharField(allow_null=True, required=False)
    carpeta = serializers.CharField(allow_null=True, required=False)
    sede = serializers.CharField(allow_null=True, required=False)
    movil = serializers.CharField(allow_null=True, required=False)
    cargo = serializers.CharField(allow_null=True, required=False)
    activo = serializers.BooleanField(allow_null=True, required=False)

    # Vehículo ASIGNADO (el `placa` de cinco_base_de_personal).
    vehiculo = VehiculoFichaSerializer(allow_null=True, required=False)
    vehiculo_placa = serializers.CharField(allow_null=True, required=False)

    # Salida de hoy y el vehículo con el que salió.
    salida = SalidaHoySerializer(allow_null=True, required=False)
    vehiculo_sale = VehiculoFichaSerializer(allow_null=True, required=False)

    nokia_disponible = serializers.BooleanField(
        required=False,
        help_text=(
            "False mientras la BD negra no esté conectada (gate G4/D-A10): "
            "la línea corporativa no se pudo consultar."
        ),
    )
