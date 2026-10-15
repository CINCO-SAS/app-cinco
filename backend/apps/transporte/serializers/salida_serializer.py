"""
Serializers de Salidas (matriz S6/B1, §5.1 y B4 backoffice).

- `SalidaSerializer`: salida a HTTP con columnas B10 (valor día /
  valor novedad / total) y permisos por fila B15 (`puede_gestionar`).
- `RegistrarSalidaSerializer`: alta S6 — conserva los nombres legacy del
  form (`movil_sale`, `cc_asignada`) para que el contrato del kiosco y
  del backoffice sea reconocible frente a `transporte_salida.php`.
- `EscanearSerializer`: contenido crudo del QR escaneado (S1: el QR D-A8
  codifica la placa).
- `AprobarLoteSerializer` / `RechazarSerializer` / `NovedadSerializer` /
  `HistorialSerializer`: acciones del backoffice B4.
"""
from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..models import Salida, SalidaHistorial, TipoNovedad
from ..models.vehiculo import Vehiculo
from ..services import SalidaService


class SalidaSerializer(serializers.ModelSerializer):
    vehiculo_placa = serializers.CharField(source="vehiculo.placa", read_only=True)
    valor_novedad = serializers.SerializerMethodField()
    total_a_pagar = serializers.SerializerMethodField()
    puede_gestionar = serializers.SerializerMethodField()

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
            "valor_novedad",
            "total_a_pagar",
            "puede_gestionar",
            "creado_en",
        ]
        read_only_fields = [
            "estado",
            "reportado",
            "valor_novedad",
            "total_a_pagar",
            "puede_gestionar",
            "creado_en",
        ]

    @extend_schema_field(Decimal)
    def get_valor_novedad(self, obj):
        """Columna B10: valor de la novedad (0 si no tiene)."""
        novedad = getattr(obj, "novedad", None)
        return novedad.valor if novedad else Decimal("0")

    @extend_schema_field(Decimal)
    def get_total_a_pagar(self, obj):
        """Columna B10: valor_dia ± novedad (única implementación)."""
        return SalidaService.calcular_pago(obj)

    @extend_schema_field(bool)
    def get_puede_gestionar(self, obj):
        """B15: jefe del área/carpeta o programación, por fila."""
        perfil = self.context.get("perfil_gestion")
        if perfil is None:
            request = self.context.get("request")
            perfil = SalidaService.perfil_gestion(
                getattr(request, "user", None)
            )
            self.context["perfil_gestion"] = perfil
        return perfil.puede_gestionar(obj.area, obj.carpeta)


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


class ValidarSerializer(serializers.Serializer):
    """S3 (kiosco): pre-chequeo de fecha/vehículo/móvil antes del alta S6."""

    fecha = serializers.DateField()
    vehiculo = serializers.PrimaryKeyRelatedField(queryset=Vehiculo.objects.all())
    movil_sale = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Cédula de quien sale (opcional) para el chequeo CR-2.",
    )


class AprobarLoteSerializer(serializers.Serializer):
    """B12: validación masiva (legacy `save_valid_transport`)."""
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="Ids de salidas en estado REPORTADO a aprobar.",
    )


class RechazarSerializer(serializers.Serializer):
    """B13: rechazo individual con motivo obligatorio (legacy lo exige
    en el modal)."""
    motivo = serializers.CharField(allow_blank=False)


class NovedadSerializer(serializers.Serializer):
    """B6: reportar novedad (modal legacy tipo/valor/descripción)."""
    tipo = serializers.ChoiceField(choices=TipoNovedad.choices)
    valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0
    )
    descripcion = serializers.CharField(allow_blank=False)


class HistorialSerializer(serializers.ModelSerializer):
    """Filas de SalidaHistorial (§7.2: historial = filas, no JSON)."""
    creado_por_cedula = serializers.SerializerMethodField()

    class Meta:
        model = SalidaHistorial
        fields = [
            "id",
            "estado",
            "motivo",
            "fecha_cambio",
            "creado_por",
            "creado_por_cedula",
        ]

    @extend_schema_field(
        serializers.CharField(allow_null=True, read_only=True)
    )
    def get_creado_por_cedula(self, obj):
        """Cédula del actor (D-A10); tolerante a historial sin actor."""
        empleado = obj.creado_por
        return empleado.cedula if empleado else None
