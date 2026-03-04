"""
Filtros personalizados para Actividades.

Este módulo proporciona utilidades para construir consultas filtradas
de actividades basadas en criterios específicos.
"""

from django.db.models import Q
from apps.operaciones.models import Actividad


class ActividadFilter:
    """Clase con métodos estáticos para filtrar actividades."""

    @staticmethod
    def filtrar_por_perfil(queryset, usuario_id):
        """
        Filtra actividades por perfil del usuario.
        Muestra las actividades que creó o aquellas donde es responsable.
        
        Args:
            queryset: QuerySet de Actividad
            usuario_id: ID del usuario actual
            
        Returns:
            QuerySet filtrado
        """
        return queryset.filter(
            Q(created_by=usuario_id) |
            Q(responsable_snapshot__empleado_id=usuario_id)
        ).distinct()

    @staticmethod
    def filtrar_por_ot(queryset, ot):
        """Filtra actividades por OT (Orden de Trabajo)."""
        return queryset.filter(ot__icontains=ot)

    @staticmethod
    def filtrar_por_estado(queryset, estado):
        """Filtra actividades por estado."""
        return queryset.filter(estado=estado)

    @staticmethod
    def filtrar_por_area(queryset, area):
        """Filtra actividades por área (responsable snapshot)."""
        return queryset.filter(responsable_snapshot__area__icontains=area)

    @staticmethod
    def filtrar_por_carpeta(queryset, carpeta):
        """Filtra actividades por carpeta (responsable snapshot)."""
        return queryset.filter(responsable_snapshot__carpeta__icontains=carpeta)

    @staticmethod
    def filtrar_por_responsable(queryset, responsable_id):
        """Filtra actividades por responsable (empleado_id)."""
        return queryset.filter(responsable_snapshot__empleado_id=responsable_id)

    @staticmethod
    def filtrar_por_zona(queryset, zona):
        """Filtra actividades por zona (ubicación)."""
        return queryset.filter(ubicacion__zona__icontains=zona)

    @staticmethod
    def filtrar_por_nodo(queryset, nodo):
        """Filtra actividades por nodo (ubicación)."""
        return queryset.filter(ubicacion__nodo__icontains=nodo)

    @staticmethod
    def buscar(queryset, termino):
        """
        Búsqueda general en múltiples campos:
        - Descripción de detalle
        - Tipo de trabajo
        - OT
        - Nombre del responsable
        """
        return queryset.filter(
            Q(detalle__descripcion__icontains=termino) |
            Q(detalle__tipo_trabajo__icontains=termino) |
            Q(ot__icontains=termino) |
            Q(responsable_snapshot__nombre__icontains=termino)
        ).distinct()

    @staticmethod
    def filtrar_por_rango_fechas(queryset, fecha_desde, fecha_hasta=None):
        """
        Filtra actividades por rango de fecha de inicio.
        
        Args:
            queryset: QuerySet de Actividad
            fecha_desde: Fecha inicial (YYYY-MM-DD)
            fecha_hasta: Fecha final (YYYY-MM-DD), opcional
            
        Returns:
            QuerySet filtrado
        """
        if fecha_desde:
            queryset = queryset.filter(fecha_inicio__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_inicio__lte=fecha_hasta)
        return queryset

    @staticmethod
    def aplicar_filtros(queryset, **filtros):
        """
        Aplica múltiples filtros al queryset.
        
        Args:
            queryset: QuerySet de Actividad
            **filtros: Diccionario con parámetros de filtro
            
        Returns:
            QuerySet filtrado
            
        Ejemplo:
            queryset = ActividadFilter.aplicar_filtros(
                queryset,
                usuario_id=1,
                ot="OT-001",
                estado="en_progreso",
                area="Soporte"
            )
        """
        if filtros.get('usuario_id'):
            queryset = ActividadFilter.filtrar_por_perfil(
                queryset, 
                filtros['usuario_id']
            )
        
        if filtros.get('ot'):
            queryset = ActividadFilter.filtrar_por_ot(queryset, filtros['ot'])
        
        if filtros.get('estado'):
            queryset = ActividadFilter.filtrar_por_estado(queryset, filtros['estado'])
        
        if filtros.get('area'):
            queryset = ActividadFilter.filtrar_por_area(queryset, filtros['area'])
        
        if filtros.get('carpeta'):
            queryset = ActividadFilter.filtrar_por_carpeta(queryset, filtros['carpeta'])
        
        if filtros.get('responsable_id'):
            queryset = ActividadFilter.filtrar_por_responsable(
                queryset, 
                filtros['responsable_id']
            )
        
        if filtros.get('zona'):
            queryset = ActividadFilter.filtrar_por_zona(queryset, filtros['zona'])
        
        if filtros.get('nodo'):
            queryset = ActividadFilter.filtrar_por_nodo(queryset, filtros['nodo'])
        
        if filtros.get('buscar'):
            queryset = ActividadFilter.buscar(queryset, filtros['buscar'])
        
        if filtros.get('fecha_inicio_desde') or filtros.get('fecha_inicio_hasta'):
            queryset = ActividadFilter.filtrar_por_rango_fechas(
                queryset,
                filtros.get('fecha_inicio_desde'),
                filtros.get('fecha_inicio_hasta')
            )
        
        return queryset
