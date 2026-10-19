"""
Serializers del WFM — F5-5.

Replican la entrada de las tres acciones del controlador legacy
(`controlador_transporte_salida_informe.php` 128–214), que llegaban por
``POST`` con un campo ``accion=...``. Aquí cada acción es su propia ruta
(contrato ADMCINCO D-A3), pero los campos y su semántica son los mismos:

- ``validarWFM``: ``area``, ``mes``, ``yyyy``, ``fecha_inicio``, ``fecha_fin``
- ``crearJobValidarWFM``: ``area``, ``mes``, ``yyyy``
- ``estadoJobValidarWFM``: ``job_uuid``

El legado rellenaba ``mes`` con ``str_pad((int)$mes, 2, '0')`` (una cadena
'10'); aquí se recibe como entero y se normaliza en el servicio, que es
donde vive la regla.
"""
from rest_framework import serializers


class WfmLoteSerializer(serializers.Serializer):
    """Entrada de ``validarWFM``: lote síncrono de validación."""

    area = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=100
    )
    mes = serializers.IntegerField(
        required=False, allow_null=True, default=None,
        help_text="Solo se usa para validar que el mes sea validable.",
    )
    yyyy = serializers.IntegerField(
        required=False, allow_null=True, default=None,
        min_value=2000, max_value=2100,
    )
    fecha_inicio = serializers.DateField(
        required=False, allow_null=True, default=None,
        help_text="INCLUSIVA (como el POST legacy); se vuelve semiabierta.",
    )
    fecha_fin = serializers.DateField(
        required=False, allow_null=True, default=None,
        help_text="INCLUSIVA (como el POST legacy).",
    )
    limite = serializers.IntegerField(
        required=False, default=25, min_value=1, max_value=100,
        help_text="Máximo de salidas por pasada (legacy 116: 1..100).",
    )


class WfmCrearJobSerializer(serializers.Serializer):
    """Entrada de ``crearJobValidarWFM``: encola y responde el job."""

    area = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=100
    )
    mes = serializers.IntegerField(
        required=False, allow_null=True, default=None, min_value=1, max_value=12
    )
    yyyy = serializers.IntegerField(
        required=False, allow_null=True, default=None,
        min_value=2000, max_value=2100,
    )


class WfmEstadoJobSerializer(serializers.Serializer):
    """Entrada de ``estadoJobValidarWFM``: consulta (+ respaldo síncrono)."""

    job_uuid = serializers.CharField(max_length=64)
