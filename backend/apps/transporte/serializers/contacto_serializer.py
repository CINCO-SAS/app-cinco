"""
Serializers de la ficha de contacto del conductor (A1).

Replica la forma de la acción `get_telefonos_conductores` del legacy
(`base_transportadores.php` 94–103) con dos mejoras:

  · `linea_corporativa` es una LISTA de números, no la cadena "300111,300222"
    que devolvía el `group_concat` del legacy.
  · Se añaden `nokia_disponible` y `tiene_contacto` para que el front
    distinga "no hay número" de "esa fuente no está disponible" (gate G2).
"""
from rest_framework import serializers


class ContactoConductorSerializer(serializers.Serializer):
    """
    Ficha de contacto de un conductor.

    Se usa como `responses` del esquema OpenAPI: los valores salen del
    servicio, no de la request.
    """

    # Placa del vehículo de referencia (null si se consultó por conductor).
    vehiculo_placa = serializers.CharField(allow_null=True, required=False)
    conductor_cedula = serializers.CharField(allow_null=True, required=False)
    conductor_nombre = serializers.CharField(allow_null=True, required=False)

    # Fuente 1: BD negra (Nokia). Vacía mientras no haya gate G2.
    linea_corporativa = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        allow_empty=True,
        required=False,
        help_text="Números de línea corporativa asignados en Nokia (BD negra).",
    )
    nokia_disponible = serializers.BooleanField(
        required=False,
        help_text=(
            "False mientras la BD negra no esté conectada (gate G2): "
            "la línea corporativa no se pudo consultar."
        ),
    )

    # Fuente 2: transporte_base_conductores (BD azul).
    celular_conductor_externo = serializers.CharField(
        allow_null=True, required=False
    )

    # Fuente 3: cinco_base_de_personal (BD azul).
    celular_personal = serializers.CharField(allow_null=True, required=False)
    celular_alterno = serializers.CharField(allow_null=True, required=False)
    telefono_fijo = serializers.CharField(allow_null=True, required=False)

    tiene_contacto = serializers.BooleanField(
        required=False,
        help_text="True si hay al menos un número disponible.",
    )
