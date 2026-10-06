from rest_framework import serializers
from apps.smu.models import (
    SmuActividad,
    SmuActividadTecnico,
    SmuActividadMaterial,
    SmuActividadEvidencia,
    SmuActividadTransporte,
    SmuActividadCierreFirma,
    SmuActividadCertificado,
    SmuDetallePreventivoAa,
    SmuDetallePreventivoAaChecklist,
    SmuPreventivoAaCompresor,
    SmuPreventivoAaCondensadora,
    SmuPreventivoAaManejadora,
    SmuPreventivoAaAccion,
    SmuDetallePreventivoPlanta,
    SmuPreventivoPlanta,
    SmuPreventivoPlantaHallazgo,
    SmuDetallePreventivoPlantaChecklist,
    SmuDetalleFallaIntervencion,
    SmuDetalleCapex,
    SmuDetalleCapexSptFila,
)
from apps.smu.services.smu_evidencia_service import TOPE_FOTOS_POR_CAMPO


# ─── B4 · Reglas de negocio del formulario SMU ───────────────────────────────
#
# Un payload es coherente cuando:
#   1. `tipo_formulario` pertenece a `SmuActividad.TIPO_FORMULARIO_CHOICES`.
#   2. el par `categoria` ↔ `tipo_formulario` corresponde a un formulario real
#      (nada de `preventivos` + `estandar`).
#   3. llega como máximo un bloque de detalle, y ese bloque corresponde al
#      tipo de formulario enviado.
TIPOS_POR_CATEGORIA = {
    'preventivos': {'aire_acondicionado', 'planta'},
    'correctivos': {'estandar'},
    'emergencias': {'estandar'},
    'correctivos_capex': {'tipologia1', 'tipologia3', 'tipologia5'},
}

DETALLES_POR_TIPO = {
    'detalle_preventivo_aa': {'aire_acondicionado'},
    'detalle_preventivo_planta': {'planta'},
    'detalle_falla_intervencion': {'estandar'},
    'detalle_capex': {'tipologia1', 'tipologia3', 'tipologia5'},
}

# Mensaje del `ChoiceField` de `tipo_formulario`, con las opciones ya
# resueltas: `Field.fail()` hace `msg.format(**kwargs)`, así que el texto no
# puede llevar marcadores que DRF no rellene.
_OPCIONES_TIPO_FORMULARIO = ", ".join(
    valor for valor, _ in SmuActividad.TIPO_FORMULARIO_CHOICES
)


class SmuActividadTecnicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuActividadTecnico
        fields = [
            'id',
            'actividad',
            'usuario',
            'cedula',
            'nombre',
            'es_principal',
            'ruta_firma',
            'ruta_certificado',
            'ruta_foto',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuActividadMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuActividadMaterial
        fields = [
            'id',
            'actividad',
            'material_lpu',
            'tipo_registro',
            'origen_material',
            'codigo_sap',
            'texto_sap',
            'alcance',
            'comentarios',
            'descripcion',
            'cantidad_estandar',
            'cantidad_real',
            'unidad_medida',
            'comprado_operario',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']



class SmuActividadEvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuActividadEvidencia
        fields = [
            'id',
            'actividad',
            'seccion',
            'campo_origen',
            'material',
            'ruta_archivo',
            'nombre_original',
            'descripcion',
            'orden',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']

    def validate_ruta_archivo(self, ruta):
        """La ruta debe apuntar a un archivo real del servidor.

        `blob:` y `data:` son URLs de preview que mueren al recargar la
        pestaña: guardarlas deja filas de evidencia que no apuntan a nada y
        que la UI no puede hidratar. Hay que subir la foto primero con
        `POST /smu/evidencias/` y enviar la `ruta_archivo` devuelta.
        """
        if isinstance(ruta, str) and ruta.strip().lower().startswith(
            ('blob:', 'data:')
        ):
            raise serializers.ValidationError(
                "No se puede guardar una URL temporal (blob:/data:). Suba la "
                "foto con POST /smu/evidencias/ y envíe la ruta_archivo que "
                "devuelve."
            )
        return ruta


class SmuActividadTransporteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuActividadTransporte
        fields = [
            'id',
            'actividad',
            'codigo_sap',
            'tipo_transporte',
            'distancia_km',
            'tiempo_traslado',
            'descripcion',
            'observacion',
        ]
        read_only_fields = ['id', 'actividad']


class SmuDetallePreventivoAaChecklistSerializer(serializers.ModelSerializer):
    # `smu_actividades.py` documenta "Del 1 al 39" sin validador de rango:
    # el campo aceptaba de 0 a 65535 y un duplicado chocaba con la unique
    # `uk_aa_actividad_item` ( IntegrityError → 400 con mensaje de BD ).
    item_numero = serializers.IntegerField(
        min_value=1,
        max_value=39,
        error_messages={
            'invalid': "item_numero debe ser un número entero del 1 al 39.",
            'min_value': "item_numero debe estar entre 1 y 39.",
            'max_value': "item_numero debe estar entre 1 y 39.",
        },
    )

    class Meta:
        model = SmuDetallePreventivoAaChecklist
        fields = [
            'id',
            'actividad',
            'item_numero',
            'estado',
        ]
        read_only_fields = ['id', 'actividad']


class SmuDetallePreventivoAaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuDetallePreventivoAa
        fields = '__all__'
        read_only_fields = ['actividad']


class SmuDetallePreventivoPlantaChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuDetallePreventivoPlantaChecklist
        fields = [
            'id',
            'actividad',
            'sistema',
            'componente',
            'estado',
            'causa',
            'detectar',
            'corregir',
        ]
        read_only_fields = ['id', 'actividad']


class SmuDetallePreventivoPlantaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuDetallePreventivoPlanta
        fields = '__all__'
        read_only_fields = ['actividad']


class SmuDetalleFallaIntervencionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuDetalleFallaIntervencion
        fields = '__all__'
        read_only_fields = ['actividad']


class SmuDetalleCapexSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuDetalleCapex
        fields = '__all__'
        read_only_fields = ['actividad']


# ─── Serializadores para modelos faltantes ─────────────────────────────────────

class SmuActividadCierreFirmaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuActividadCierreFirma
        fields = [
            'id',
            'actividad',
            'rol',
            'nombre',
            'cedula',
            'cargo',
            'fecha',
            'ruta_firma',
            'orden',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuActividadCertificadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuActividadCertificado
        fields = [
            'id',
            'actividad',
            'tipo',
            'categoria',
            'ruta_certificado',
            'ruta_foto_sitio',
            'orden',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuPreventivoAaCompresorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuPreventivoAaCompresor
        fields = [
            'id',
            'actividad',
            'orden',
            'marca',
            'serial',
            'tipo',
            'refrigerante',
            'modelo',
            'aislamiento_electrico',
            'presion_succion',
            'presion_descarga',
            'nivel_aceite',
            'vl1',
            'vl2',
            'vl3',
            'amp_l1',
            'amp_l2',
            'amp_l3',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuPreventivoAaCondensadoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuPreventivoAaCondensadora
        fields = [
            'id',
            'actividad',
            'orden',
            'marca',
            'modelo',
            'serial',
            'temperatura_entrada',
            'temperatura_salida',
            'diametro_eje',
            'diametro_aspas',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuPreventivoAaManejadoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuPreventivoAaManejadora
        fields = [
            'id',
            'actividad',
            'orden',
            'marca',
            'modelo',
            'tipo',
            'tipo_filtro',
            'tipo_correa',
            'marca_motor',
            'alimentacion_ac',
            'voltaje',
            'corriente',
            'aislamiento',
            'serial_motor',
            'dimensiones_blower',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuPreventivoAaAccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuPreventivoAaAccion
        fields = [
            'id',
            'actividad',
            'clave',
            'valor',
            'orden',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuPreventivoPlantaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuPreventivoPlanta
        fields = '__all__'
        read_only_fields = ['actividad']


class SmuPreventivoPlantaHallazgoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuPreventivoPlantaHallazgo
        fields = [
            'id',
            'actividad',
            'orden',
            'descripcion',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuDetalleCapexSptFilaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmuDetalleCapexSptFila
        fields = [
            'id',
            'actividad',
            'orden',
            'distancia',
            'medida_ohmio',
            'resistividad',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'actividad']


class SmuActividadSerializer(serializers.ModelSerializer):
    # Texto libre → enumeración validada (B4). El modelo no lleva `choices=`
    # en el campo para no generar una migración pendiente.
    tipo_formulario = serializers.ChoiceField(
        choices=SmuActividad.TIPO_FORMULARIO_CHOICES,
        error_messages={
            'invalid_choice': (
                f"tipo_formulario no es válido. Opciones válidas: "
                f"{_OPCIONES_TIPO_FORMULARIO}."
            ),
        },
    )
    tecnicos = SmuActividadTecnicoSerializer(many=True, required=False)
    materiales = SmuActividadMaterialSerializer(many=True, required=False)
    evidencias = SmuActividadEvidenciaSerializer(many=True, required=False)
    transportes = SmuActividadTransporteSerializer(many=True, required=False)
    
    checklist_aa = SmuDetallePreventivoAaChecklistSerializer(many=True, required=False)
    detalle_preventivo_aa = SmuDetallePreventivoAaSerializer(required=False, allow_null=True)
    
    checklist_planta = SmuDetallePreventivoPlantaChecklistSerializer(many=True, required=False)
    detalle_preventivo_planta = SmuDetallePreventivoPlantaSerializer(required=False, allow_null=True)
    
    detalle_falla_intervencion = SmuDetalleFallaIntervencionSerializer(required=False, allow_null=True)
    detalle_capex = SmuDetalleCapexSerializer(required=False, allow_null=True)

    # Relaciones anidadas faltantes
    firmas_cierre = SmuActividadCierreFirmaSerializer(many=True, required=False)
    certificados = SmuActividadCertificadoSerializer(many=True, required=False)
    aa_compresores = SmuPreventivoAaCompresorSerializer(many=True, required=False)
    aa_condensadoras = SmuPreventivoAaCondensadoraSerializer(many=True, required=False)
    aa_manejadoras = SmuPreventivoAaManejadoraSerializer(many=True, required=False)
    aa_acciones = SmuPreventivoAaAccionSerializer(many=True, required=False)
    plantas = SmuPreventivoPlantaSerializer(many=True, required=False)
    hallazgos_planta = SmuPreventivoPlantaHallazgoSerializer(many=True, required=False)
    spt_filas = SmuDetalleCapexSptFilaSerializer(many=True, required=False)

    class Meta:
        model = SmuActividad
        fields = [
            'id',
            'categoria',
            'tipo_formulario',
            'codigo_ot',
            'actividad_operaciones',
            'numero_inc',
            'numero_tas',
            'estacion',
            'nombre_estacion',
            'tipo_estacion',
            'tipo_sitio',
            'categoria_criticidad',
            'site_owner',
            'regional',
            'departamento',
            'direccion',
            'fecha_inicio',
            'fecha_fin',
            'responsable',
            'responsable_cedula',
            'responsable_nombre',
            'coordinador_aliado',
            'empresa',
            'implica_exclusion',
            'observaciones',
            'hallazgos',
            'recomendaciones',
            'estado',
            'created_at',
            'updated_at',
            # Relaciones anidadas existentes
            'tecnicos',
            'materiales',
            'evidencias',
            'transportes',
            'detalle_preventivo_aa',
            'checklist_aa',
            'detalle_preventivo_planta',
            'checklist_planta',
            'detalle_falla_intervencion',
            'detalle_capex',
            # Relaciones anidadas faltantes
            'firmas_cierre',
            'certificados',
            'aa_compresores',
            'aa_condensadoras',
            'aa_manejadoras',
            'aa_acciones',
            'plantas',
            'hallazgos_planta',
            'spt_filas',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        fecha_inicio = attrs.get('fecha_inicio')
        fecha_fin = attrs.get('fecha_fin')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError({
                'fecha_fin': "La fecha de fin no puede ser anterior a la fecha de inicio."
            })
        self._validar_rango_fechas(attrs)
        # En creación inicial, no permitir auto-aprobar directamente
        if self.instance is None and attrs.get('estado') == 'aprobado':
            attrs['estado'] = 'enviado'

        self._validar_coherencia_formulario(attrs)
        self._validar_detalles_del_formulario(attrs)
        self._validar_tope_evidencias(attrs)

        return attrs

    # Rango de años creíble para las fechas del encabezado.
    ANIO_MINIMO = 1900
    ANIO_MAXIMO = 2100

    def _validar_rango_fechas(self, attrs):
        """Rechaza años absurdos (p. ej. la digitación ``12/12/1212``).

        Una fecha así se guardaba sin más y la tabla de historial no puede
        formatearla: DRF la serializa con el offset histórico del año
        (``1212-12-12T00:12:00-04:56:16``) y ``new Date()`` la marca inválida,
        con lo que la columna "INICIO" quedaba en "-". El frontend valida lo
        mismo antes de enviar; aquí se protege la API para cualquier cliente.
        """
        for campo in ('fecha_inicio', 'fecha_fin'):
            valor = attrs.get(campo)
            if valor is None:
                continue
            if not (self.ANIO_MINIMO <= valor.year <= self.ANIO_MAXIMO):
                raise serializers.ValidationError({
                    campo: (
                        f"El año {valor.year} está fuera del rango permitido "
                        f"({self.ANIO_MINIMO}-{self.ANIO_MAXIMO})."
                    )
                })

    def _validar_coherencia_formulario(self, attrs):
        """B4: el par `categoria` ↔ `tipo_formulario` debe corresponder a uno
        de los 4 formularios del módulo (antes `preventivos` + `estandar`
        se guardaba igual).

        En un PATCH parcial, lo que no llega en el payload se lee de la
        instancia para poder evaluar la regla de todas formas.
        """
        categoria = attrs.get('categoria') or getattr(self.instance, 'categoria', None)
        tipo = (
            attrs.get('tipo_formulario')
            or getattr(self.instance, 'tipo_formulario', None)
        )
        if not categoria or not tipo:
            return

        permitidos = TIPOS_POR_CATEGORIA.get(categoria)
        if permitidos and tipo not in permitidos:
            raise serializers.ValidationError({
                'tipo_formulario': (
                    f"El tipo de formulario '{tipo}' no corresponde a la categoría "
                    f"'{categoria}'. Opciones válidas: "
                    f"{', '.join(sorted(permitidos))}."
                ),
            })

    def _validar_detalles_del_formulario(self, attrs):
        """B4: máximo un bloque de detalle por actividad, y debe corresponder
        al `tipo_formulario` enviado (antes se aceptaban dos a la vez).
        """
        presentes = [clave for clave in DETALLES_POR_TIPO if attrs.get(clave)]

        if len(presentes) > 1:
            raise serializers.ValidationError(
                "Solo puede enviarse un bloque de detalle por actividad; "
                f"se recibieron: {', '.join(presentes)}."
            )

        if not presentes:
            return

        tipo = (
            attrs.get('tipo_formulario')
            or getattr(self.instance, 'tipo_formulario', None)
        )
        if not tipo:
            return

        clave = presentes[0]
        if tipo not in DETALLES_POR_TIPO[clave]:
            raise serializers.ValidationError({
                clave: (
                    f"El bloque '{clave}' no corresponde al tipo de formulario "
                    f"'{tipo}'."
                ),
            })

    def _validar_tope_evidencias(self, attrs):
        """A1: máximo `TOPE_FOTOS_POR_CAMPO` fotos por `campo_origen`.

        Regla portada del PHP (`$maxArchivos = 5` en
        `capex_procesar_archivos`). El límite se aplica sobre el payload en
        creación, que es cuando se suben las fotos (al guardar el formulario)
        y todavía no hay filas en la base que contar.
        """
        evidencias = attrs.get('evidencias')
        if not evidencias:
            return

        conteo = {}
        for evidencia in evidencias:
            campo = evidencia.get('campo_origen') or 'campo'
            conteo[campo] = conteo.get(campo, 0) + 1

        excedidos = {
            campo: total
            for campo, total in conteo.items()
            if total > TOPE_FOTOS_POR_CAMPO
        }
        if excedidos:
            detalle = ', '.join(
                f"'{campo}' ({total})"
                for campo, total in sorted(excedidos.items())
            )
            raise serializers.ValidationError(
                f"Máximo {TOPE_FOTOS_POR_CAMPO} fotos por campo; "
                f"exceden el límite: {detalle}."
            )
