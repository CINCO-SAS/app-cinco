"""
Serializers de Salidas (matriz S6/B1, §5.1 y B4 backoffice).

- `SalidaSerializer`: salida a HTTP con columnas B10 (valor día /
  valor novedad / total) y permisos por fila B15 (`puede_gestionar`), más
  el detalle de las personas (`conductor_detalle` / `tecnico_asignado_detalle`)
  para pintar la tabla sin recurrir a los PK.
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

# Anotación OpenAPI de los "*_detalle": objeto {nombre, cedula} o null.
# Es SOLO un esquema (no un campo declarado) y por eso vive fuera de la clase:
# dentro, el `SerializerMetaclass` lo metería en `_declared_fields`.
DETALLE_ESQUEMA = serializers.DictField(
    child=serializers.CharField(allow_null=True), allow_null=True
)

# Anotación OpenAPI de `novedad_detalle`: objeto {tipo, valor, descripcion} o
# null. Misma razón que DETALLE_ESQUEMA: es documentación, no un campo real.
NOVEDAD_ESQUEMA = serializers.DictField(
    child=serializers.CharField(allow_null=True), allow_null=True
)


class SalidaSerializer(serializers.ModelSerializer):
    vehiculo_placa = serializers.CharField(source="vehiculo.placa", read_only=True)
    valor_novedad = serializers.SerializerMethodField()
    total_a_pagar = serializers.SerializerMethodField()
    puede_gestionar = serializers.SerializerMethodField()
    conductor_detalle = serializers.SerializerMethodField()
    tecnico_asignado_detalle = serializers.SerializerMethodField()
    novedad_detalle = serializers.SerializerMethodField()

    class Meta:
        model = Salida
        fields = [
            "id",
            "vehiculo",
            "vehiculo_placa",
            "fecha_salida",
            "conductor",
            "conductor_detalle",
            "tecnico_asignado",
            "tecnico_asignado_detalle",
            "es_disponible",
            "area",
            "carpeta",
            "sede",
            "valor_dia",
            "estado",
            "observacion",
            "reportado",
            "valor_novedad",
            "novedad_detalle",
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

    @extend_schema_field(DETALLE_ESQUEMA)
    def get_conductor_detalle(self, obj):
        """Columna 'quién sale' (legacy ``movil_sale``) de la tabla B1.

        Devuelve ``{nombre, cedula}`` o ``None`` si no hay conductor (p. ej.
        salidas 'disponible'): el backoffice pinta personas, no PKs. Ambos
        detalles usan la MISMA forma para que el front tenga un solo shape.
        """
        conductor = obj.conductor
        if conductor is None:
            return None
        return {"nombre": conductor.nombre_completo, "cedula": conductor.cedula}

    @extend_schema_field(DETALLE_ESQUEMA)
    def get_tecnico_asignado_detalle(self, obj):
        """Columna 'móvil asignada' (legacy ``cc_asignada`` → Empleado nómina).

        ADVERTENCIA cross-DB: ``tecnico_asignado`` vive en **azul**, así que
        SOLO debe tocarse con la fila ya prefetcheada. Todas las rutas que
        serializan muchas filas pasan por
        ``prefetch_related("tecnico_asignado")`` (listar, obtener, mensual,
        aprobar_masivo) — sin eso el endpoint cae a N+1 contra otra BD.
        """
        tecnico = obj.tecnico_asignado
        if tecnico is None:
            return None
        nombre = " ".join(
            parte for parte in (tecnico.nombre, tecnico.apellido) if parte
        )
        return {"nombre": nombre, "cedula": tecnico.cedula}

    @extend_schema_field(NOVEDAD_ESQUEMA)
    def get_novedad_detalle(self, obj):
        """Novedad ADICIONAL/DESCUENTO de la salida, o ``None`` (B6/B7).

        Existe para que el front no borre a ciegas: `valor_novedad` dice
        CUÁNTO, pero no QUÉ era ni POR QUÉ. Al menos una por salida (regla
        de negocio heredada del legacy, reforzada en `registrar_novedad`).

        Se resuelve con `select_related("novedad")` en `listar`/`obtener`
        (Django acepta OneToOne inverso ahí), así que no añade consultas.
        """
        novedad = getattr(obj, "novedad", None)
        if novedad is None:
            return None
        # Cadena explícita: `SerializerMethodField` devuelve el valor CRUDO y
        # `Decimal`/`TextChoices` no siempre sobreviven al JSONRenderer.
        # `format` (y no `str`) mantiene los 2 decimales fijos que DRF aplica
        # a sus propios `DecimalField`, así el front ve un shape uniforme.
        return {
            "tipo": str(novedad.tipo),
            "valor": format(novedad.valor, "f"),
            "descripcion": novedad.descripcion,
        }


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


class IdentificarVehiculoSerializer(serializers.Serializer):
    """S1/S4 (kiosco): identifica vehículo por placa o por QR decodificado."""
    placa = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Placa directa del vehículo.",
    )
    qr = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Texto decodificado del código QR.",
    )
    contenido = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Alias de compatibilidad para el contenido del QR.",
    )

    def validate(self, attrs):
        valor = attrs.get("placa") or attrs.get("qr") or attrs.get("contenido") or ""
        valor = valor.strip().upper()
        if not valor:
            raise serializers.ValidationError(
                "Debe proporcionar la placa o el contenido del QR."
            )
        attrs["placa"] = valor
        return attrs


EscanearSerializer = IdentificarVehiculoSerializer


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
