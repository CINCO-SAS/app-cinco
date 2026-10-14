"""
Registro de modelos del módulo Transporte en el admin de Django.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §3.
"""
from django.contrib import admin

from .models import (
    AuditoriaLog,
    Conductor,
    ConsecutivoMensual,
    DatosBancariosVehiculo,
    DocumentoVehiculo,
    FechaLimiteCierre,
    JefeValidador,
    Mantenimiento,
    Novedad,
    PagoVehiculoMensual,
    ReporteFotograficoVehiculo,
    Salida,
    SalidaHistorial,
    ValidacionSalida,
    Vehiculo,
)


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ("cedula", "nombre_completo", "celular", "tipo_vinculacion", "activo")
    list_filter = ("tipo_vinculacion", "activo")
    search_fields = ("cedula", "nombre_completo", "celular")


class DocumentoVehiculoInline(admin.TabularInline):
    model = DocumentoVehiculo
    extra = 0


class MantenimientoInline(admin.TabularInline):
    model = Mantenimiento
    extra = 0


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "marca", "tipo_vehiculo", "tipo_contrato", "activo")
    list_filter = ("tipo_vehiculo", "tipo_contrato", "ciudad_operacion", "activo")
    search_fields = ("placa", "marca", "numero_vin", "numero_motor")
    inlines = [DocumentoVehiculoInline, MantenimientoInline]


class SalidaHistorialInline(admin.TabularInline):
    model = SalidaHistorial
    extra = 0
    readonly_fields = ("estado", "motivo", "fecha_cambio", "creado_por")


@admin.register(Salida)
class SalidaAdmin(admin.ModelAdmin):
    list_display = ("id", "vehiculo", "fecha_salida", "estado", "valor_dia", "reportado")
    list_filter = ("estado", "fecha_salida", "es_disponible", "reportado")
    search_fields = ("vehiculo__placa", "conductor__cedula", "tecnico_asignado__cedula")
    inlines = [SalidaHistorialInline]


@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ("salida", "tipo", "valor")
    list_filter = ("tipo",)


@admin.register(FechaLimiteCierre)
class FechaLimiteCierreAdmin(admin.ModelAdmin):
    list_display = ("mes", "anio", "fecha_limite")
    list_filter = ("anio",)


@admin.register(ConsecutivoMensual)
class ConsecutivoMensualAdmin(admin.ModelAdmin):
    list_display = ("vehiculo", "mes", "anio", "consecutivo")
    list_filter = ("anio", "mes")


@admin.register(PagoVehiculoMensual)
class PagoVehiculoMensualAdmin(admin.ModelAdmin):
    list_display = ("vehiculo", "mes", "anio", "tipo", "pagado", "total_liquidado")
    list_filter = ("tipo", "pagado", "anio")


@admin.register(JefeValidador)
class JefeValidadorAdmin(admin.ModelAdmin):
    list_display = ("empleado", "activo")
    list_filter = ("activo",)


@admin.register(ValidacionSalida)
class ValidacionSalidaAdmin(admin.ModelAdmin):
    list_display = ("area", "mes", "anio")
    list_filter = ("anio",)


@admin.register(ReporteFotograficoVehiculo)
class ReporteFotograficoVehiculoAdmin(admin.ModelAdmin):
    list_display = ("vehiculo", "fecha", "hora", "responsable")
    list_filter = ("fecha",)


@admin.register(AuditoriaLog)
class AuditoriaLogAdmin(admin.ModelAdmin):
    list_display = ("tabla", "accion", "registro_id", "creado_en")
    list_filter = ("tabla", "accion")
    readonly_fields = ("tabla", "accion", "registro_id", "datos_antes", "datos_despues")
