from django.contrib import admin
from apps.smu.models import (
    SmuEstacion,
    SmuMatrizLpu,
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


@admin.register(SmuEstacion)
class SmuEstacionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'nombre_sitio',
        'regional',
        'departamento',
        'municipio',
        'tipo_estacion',
        'tipo_sitio',
        'categoria_criticidad',
        'activo',
    ]
    search_fields = [
        'nombre_sitio',
        'regional',
        'departamento',
        'municipio',
        'site_owner',
    ]
    list_filter = ['regional', 'departamento', 'tipo_estacion', 'categoria_criticidad', 'activo']
    ordering = ['nombre_sitio']


@admin.register(SmuMatrizLpu)
class SmuMatrizLpuAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'codigo_sap',
        'codigo_liquidacion',
        'texto_sap',
        'unidad_medida',
        'valor_unitario',
        'tipo_registro',
        'activo',
    ]
    search_fields = [
        'codigo_sap',
        'codigo_liquidacion',
        'texto_sap',
        'descripcion',
    ]
    list_filter = ['tipo_registro', 'activo', 'fecha_vigencia_inicio']
    ordering = ['codigo_sap']


class SmuActividadTecnicoInline(admin.TabularInline):
    model = SmuActividadTecnico
    extra = 0
    autocomplete_fields = ['usuario']


class SmuActividadMaterialInline(admin.TabularInline):
    model = SmuActividadMaterial
    extra = 0
    autocomplete_fields = ['material_lpu']


class SmuActividadEvidenciaInline(admin.TabularInline):
    model = SmuActividadEvidencia
    extra = 0


class SmuActividadTransporteInline(admin.TabularInline):
    model = SmuActividadTransporte
    extra = 0


class SmuDetallePreventivoAaInline(admin.StackedInline):
    model = SmuDetallePreventivoAa
    extra = 0


class SmuDetallePreventivoAaChecklistInline(admin.TabularInline):
    model = SmuDetallePreventivoAaChecklist
    extra = 0


class SmuDetallePreventivoPlantaInline(admin.StackedInline):
    model = SmuDetallePreventivoPlanta
    extra = 0


class SmuDetallePreventivoPlantaChecklistInline(admin.TabularInline):
    model = SmuDetallePreventivoPlantaChecklist
    extra = 0


class SmuDetalleFallaIntervencionInline(admin.StackedInline):
    model = SmuDetalleFallaIntervencion
    extra = 0


class SmuDetalleCapexInline(admin.StackedInline):
    model = SmuDetalleCapex
    extra = 0


class SmuActividadCierreFirmaInline(admin.TabularInline):
    model = SmuActividadCierreFirma
    extra = 0


class SmuActividadCertificadoInline(admin.TabularInline):
    model = SmuActividadCertificado
    extra = 0


class SmuPreventivoAaCompresorInline(admin.TabularInline):
    model = SmuPreventivoAaCompresor
    extra = 0


class SmuPreventivoAaCondensadoraInline(admin.TabularInline):
    model = SmuPreventivoAaCondensadora
    extra = 0


class SmuPreventivoAaManejadoraInline(admin.TabularInline):
    model = SmuPreventivoAaManejadora
    extra = 0


class SmuPreventivoAaAccionInline(admin.TabularInline):
    model = SmuPreventivoAaAccion
    extra = 0


class SmuPreventivoPlantaInline(admin.TabularInline):
    model = SmuPreventivoPlanta
    extra = 0


class SmuPreventivoPlantaHallazgoInline(admin.TabularInline):
    model = SmuPreventivoPlantaHallazgo
    extra = 0


class SmuDetalleCapexSptFilaInline(admin.TabularInline):
    model = SmuDetalleCapexSptFila
    extra = 0


@admin.register(SmuActividad)
class SmuActividadAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'categoria',
        'tipo_formulario',
        'estacion',
        'nombre_estacion',
        'codigo_ot',
        'numero_inc',
        'responsable',
        'responsable_cedula',
        'estado',
        'created_at',
    ]
    list_filter = ['categoria', 'tipo_formulario', 'estado', 'created_at', 'regional']
    search_fields = [
        '=id',
        'nombre_estacion',
        'codigo_ot',
        'numero_inc',
        'numero_tas',
        'responsable_cedula',
        'responsable_nombre',
    ]
    autocomplete_fields = ['estacion', 'responsable', 'actividad_operaciones']
    inlines = [
        SmuActividadTecnicoInline,
        SmuActividadMaterialInline,
        SmuActividadEvidenciaInline,
        SmuActividadTransporteInline,
        SmuActividadCierreFirmaInline,
        SmuActividadCertificadoInline,
        SmuDetallePreventivoAaInline,
        SmuDetallePreventivoAaChecklistInline,
        SmuPreventivoAaCompresorInline,
        SmuPreventivoAaCondensadoraInline,
        SmuPreventivoAaManejadoraInline,
        SmuPreventivoAaAccionInline,
        SmuDetallePreventivoPlantaInline,
        SmuDetallePreventivoPlantaChecklistInline,
        SmuPreventivoPlantaInline,
        SmuPreventivoPlantaHallazgoInline,
        SmuDetalleFallaIntervencionInline,
        SmuDetalleCapexInline,
        SmuDetalleCapexSptFilaInline,
    ]


@admin.register(SmuActividadTecnico)
class SmuActividadTecnicoAdmin(admin.ModelAdmin):
    list_display = ['id', 'actividad', 'usuario', 'cedula', 'nombre', 'es_principal', 'created_at']
    search_fields = ['cedula', 'nombre', '=actividad__id']
    autocomplete_fields = ['usuario']


@admin.register(SmuActividadMaterial)
class SmuActividadMaterialAdmin(admin.ModelAdmin):
    list_display = ['id', 'actividad', 'material_lpu', 'tipo_registro', 'codigo_sap', 'cantidad_real', 'unidad_medida', 'comprado_operario']
    search_fields = ['codigo_sap', 'texto_sap', '=actividad__id']
    autocomplete_fields = ['material_lpu']


@admin.register(SmuActividadEvidencia)
class SmuActividadEvidenciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'actividad', 'seccion', 'campo_origen', 'ruta_archivo', 'orden']
    search_fields = ['seccion', 'campo_origen', 'actividad__id']


@admin.register(SmuActividadTransporte)
class SmuActividadTransporteAdmin(admin.ModelAdmin):
    list_display = ['id', 'actividad', 'codigo_sap', 'tipo_transporte', 'distancia_km', 'tiempo_traslado']
    search_fields = ['codigo_sap', 'tipo_transporte', 'actividad__id']
