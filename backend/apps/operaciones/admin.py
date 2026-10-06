from django.contrib import admin
from apps.operaciones.models.actividad_model import Actividad, ActividadOT


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ['id', 'ot', 'estado', 'responsable_id', 'fecha_inicio', 'fecha_fin_estimado']
    search_fields = ['id', 'ot']
    list_filter = ['estado', 'fecha_inicio']


@admin.register(ActividadOT)
class ActividadOTAdmin(admin.ModelAdmin):
    list_display = ['id', 'actividad', 'ot', 'is_active', 'created_at']
    search_fields = ['ot', 'actividad__id']
    list_filter = ['is_active']
