from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from apps.operaciones.models import (
    Actividad,
    ActividadDetalle,
    ActividadUbicacion,
    ActividadResponsableSnapshot
)
from apps.empleados.services import EmpleadoService

class ActividadService:

    # @staticmethod
    def crear(self, data: dict) -> Actividad:
        detalle_data = data.pop('detalle')
        ubicacion_data = data.pop('ubicacion')

        with transaction.atomic():
            # 1️⃣ Obtener empleado desde otra DB
            empleado = EmpleadoService().obtener_basico(data['responsable_id'])
            
            # datos de la sesión actual
            data['created_by'] = self.request.user.id
            data['updated_by'] = self.request.user.id
            
            actividad = Actividad.objects.create(**data)

            # 3️⃣ Snapshot del responsable
            ActividadResponsableSnapshot.objects.create(
                actividad=actividad,
                empleado_id=empleado['id'],
                nombre=empleado['nombre'],
                area=empleado['area'],
                carpeta=empleado['carpeta'],
                cargo=empleado['cargo'],
                movil=empleado['movil'],
            )

            # 4️⃣ Ubicación
            ActividadUbicacion.objects.create(
                actividad=actividad,
                **ubicacion_data
            )

            # 5️⃣ Detalle
            ActividadDetalle.objects.create(
                actividad=actividad,
                **detalle_data
            )

            return actividad

    @staticmethod
    def listar(usuario_id=None, **filtros):
        """
        Lista actividades con filtros según perfil y parámetros de búsqueda.
        
        Args:
            usuario_id: ID del usuario actual para filtrar por creador o responsable
            **filtros: Parámetros adicionales (ot, area, carpeta, estado, etc.)
        """
        queryset = Actividad.objects.filter(is_deleted=False)
        
        # 1️⃣ Filtrar por perfil del usuario (creador O responsable)
        if usuario_id:
            queryset = queryset.filter(
                Q(created_by=usuario_id) |
                Q(responsable_snapshot__empleado_id=usuario_id)
            ).distinct()
        
        # 2️⃣ Filtrar por OT
        if filtros.get('ot'):
            queryset = queryset.filter(ot__icontains=filtros['ot'])
        
        # 3️⃣ Filtrar por estado
        if filtros.get('estado'):
            queryset = queryset.filter(estado=filtros['estado'])
        
        # 4️⃣ Filtrar por área
        if filtros.get('area'):
            queryset = queryset.filter(
                responsable_snapshot__area__icontains=filtros['area']
            )
        
        # 5️⃣ Filtrar por carpeta
        if filtros.get('carpeta'):
            queryset = queryset.filter(
                responsable_snapshot__carpeta__icontains=filtros['carpeta']
            )
        
        # 6️⃣ Búsqueda general en descripción y tipo de trabajo
        if filtros.get('buscar'):
            buscar = filtros['buscar']
            queryset = queryset.filter(
                Q(detalle__descripcion__icontains=buscar) |
                Q(detalle__tipo_trabajo__icontains=buscar) |
                Q(ot__icontains=buscar) |
                Q(responsable_snapshot__nombre__icontains=buscar)
            ).distinct()
        
        # 7️⃣ Filtrar por responsable (empleado_id)
        if filtros.get('responsable_id'):
            queryset = queryset.filter(
                responsable_snapshot__empleado_id=filtros['responsable_id']
            )
        
        # 8️⃣ Filtrar por fecha inicio
        if filtros.get('fecha_inicio_desde'):
            queryset = queryset.filter(
                fecha_inicio__gte=filtros['fecha_inicio_desde']
            )
        
        if filtros.get('fecha_inicio_hasta'):
            queryset = queryset.filter(
                fecha_inicio__lte=filtros['fecha_inicio_hasta']
            )
        
        # 9️⃣ Filtrar por zona y nodo
        if filtros.get('zona'):
            queryset = queryset.filter(
                ubicacion__zona__icontains=filtros['zona']
            )
        
        if filtros.get('nodo'):
            queryset = queryset.filter(
                ubicacion__nodo__icontains=filtros['nodo']
            )
        
        return queryset
