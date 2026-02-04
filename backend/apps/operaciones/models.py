from django.db import models
from django.utils import timezone

class ActividadModel(models.Model):
    """Modelo para gestionar actividades operacionales"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    # id
    # ticket?
    # fecha_creacion
    # ot
    # 
    
    id = models.AutoField(primary_key=True)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    # area = models.ForeignKey('AreaModel', on_delete=models.CASCADE, related_name='actividades')
    # empleado = models.ForeignKey('EmpleadoModel', on_delete=models.CASCADE, related_name='actividades')
    # movil = models.ForeignKey('MovilModel', on_delete=models.CASCADE, related_name='actividades')
    
    
    
    
    class Meta:
        db_table = 'operaciones_actividades'
        app_label = 'azul'
        # verbose_name = 'Actividad'
        # verbose_name_plural = 'Actividades'
        # ordering = ['-fecha_creacion']
    