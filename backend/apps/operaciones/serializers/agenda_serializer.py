from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.operaciones.models.actividad_model import Actividad
from apps.operaciones.models.agenda_model import Agenda

User = get_user_model()


class AgendaMesQuerySerializer(serializers.Serializer):
    """
    Parámetros de consulta para filtrar agendamientos por mes/año, rango de fechas y/o sede.
    """
    mes = serializers.CharField(
        max_length=2,
        required=False,
        help_text="Mes a consultar (01 a 12)"
    )
    yyyy = serializers.CharField(
        max_length=4,
        required=False,
        help_text="Año a consultar (ej. 2026)"
    )
    fecha_inicio = serializers.DateField(
        required=False,
        help_text="Filtro opcional fecha inicio rango"
    )
    fecha_fin = serializers.DateField(
        required=False,
        help_text="Filtro opcional fecha fin rango"
    )
    sede = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Filtrar por sede (medellin, monteria, sincelejo, etc.)"
    )
    responsable_id = serializers.IntegerField(
        required=False,
        help_text="Filtrar por ID de técnico (auth_user)"
    )
    actividad_id = serializers.IntegerField(
        required=False,
        help_text="Filtrar por ID de actividad"
    )


class AgendaReadSerializer(serializers.ModelSerializer):
    """
    Serializador de lectura que devuelve la información completa del agendamiento,
    incluyendo los datos relacionados de la OT, ubicación y técnico en una sola respuesta.
    """
    # Datos de la Actividad / OT
    ot = serializers.CharField(source="actividad.ot", read_only=True)
    actividad_estado = serializers.CharField(source="actividad.estado", read_only=True)
    tipo_trabajo = serializers.SerializerMethodField()
    descripcion = serializers.SerializerMethodField()
    
    # Datos de Ubicación de la actividad
    direccion = serializers.SerializerMethodField()
    zona = serializers.SerializerMethodField()
    nodo = serializers.SerializerMethodField()
    latitud = serializers.SerializerMethodField()
    longitud = serializers.SerializerMethodField()

    # Datos del Técnico / Responsable (auth_user)
    responsable_id = serializers.IntegerField(source="responsable.id", read_only=True)
    responsable_cedula = serializers.CharField(source="responsable.username", read_only=True)
    cedula = serializers.CharField(source="responsable.username", read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    responsable_email = serializers.CharField(source="responsable.email", read_only=True)
    responsable_cargo = serializers.SerializerMethodField()
    responsable_area = serializers.SerializerMethodField()
    responsable_carpeta = serializers.SerializerMethodField()
    responsable_movil = serializers.SerializerMethodField()
    responsable_link_foto = serializers.SerializerMethodField()

    class Meta:
        model = Agenda
        fields = [
            "id",
            "actividad_id",
            "ot",
            "actividad_estado",
            "tipo_trabajo",
            "descripcion",
            "direccion",
            "zona",
            "nodo",
            "latitud",
            "longitud",
            "responsable_id",
            "responsable_cedula",
            "cedula",
            "responsable_nombre",
            "responsable_email",
            "responsable_cargo",
            "responsable_area",
            "responsable_carpeta",
            "responsable_movil",
            "responsable_link_foto",
            "fecha_inicio",
            "fecha_fin",
            "sede",
            "color_hex",
            "observacion",
            "created_at",
            "updated_at",
        ]

    def get_tipo_trabajo(self, obj) -> str:
        detalle = getattr(obj.actividad, "detalle", None)
        return detalle.tipo_trabajo if detalle else ""

    def get_descripcion(self, obj) -> str:
        detalle = getattr(obj.actividad, "detalle", None)
        return detalle.descripcion if detalle else ""

    def get_direccion(self, obj) -> str:
        ubicacion = getattr(obj.actividad, "ubicacion", None)
        return ubicacion.direccion if ubicacion else ""

    def get_zona(self, obj) -> str:
        ubicacion = getattr(obj.actividad, "ubicacion", None)
        return ubicacion.zona if ubicacion else ""

    def get_nodo(self, obj) -> str:
        ubicacion = getattr(obj.actividad, "nodo", None) or getattr(obj.actividad, "ubicacion", None)
        return getattr(ubicacion, "nodo", "") if ubicacion else ""

    def get_latitud(self, obj) -> str:
        ubicacion = getattr(obj.actividad, "ubicacion", None)
        return getattr(ubicacion, "coordenada_y", "") if ubicacion else ""

    def get_longitud(self, obj) -> str:
        ubicacion = getattr(obj.actividad, "ubicacion", None)
        return getattr(ubicacion, "coordenada_x", "") if ubicacion else ""

    def _get_empleado_info(self, obj):
        if not hasattr(self, "_empleados_cache"):
            self._empleados_cache = {}
        if not obj.responsable or not obj.responsable.username:
            return None
        ced = str(obj.responsable.username)
        if ced not in self._empleados_cache:
            try:
                from apps.empleados.models.empleado_model import Empleado
                self._empleados_cache[ced] = Empleado.objects.filter(cedula=ced).first()
            except Exception:
                self._empleados_cache[ced] = None
        return self._empleados_cache[ced]

    def get_responsable_nombre(self, obj) -> str:
        emp = self._get_empleado_info(obj)
        if emp:
            nombre = f"{emp.nombre} {emp.apellido}".strip()
            if nombre:
                return nombre
        if obj.responsable:
            nombre_completo = obj.responsable.get_full_name().strip()
            if nombre_completo:
                return nombre_completo
            return obj.responsable.username
        snapshot = getattr(obj.actividad, "responsable_snapshot", None)
        if snapshot and snapshot.nombre:
            return snapshot.nombre
        return ""

    def get_responsable_cargo(self, obj) -> str:
        emp = self._get_empleado_info(obj)
        if emp and emp.cargo:
            return emp.cargo
        snapshot = getattr(obj.actividad, "responsable_snapshot", None)
        return snapshot.cargo if snapshot else ""

    def get_responsable_area(self, obj) -> str:
        emp = self._get_empleado_info(obj)
        if emp and emp.area:
            return emp.area
        snapshot = getattr(obj.actividad, "responsable_snapshot", None)
        return snapshot.area if snapshot else ""

    def get_responsable_carpeta(self, obj) -> str:
        emp = self._get_empleado_info(obj)
        if emp and emp.carpeta:
            return emp.carpeta
        snapshot = getattr(obj.actividad, "responsable_snapshot", None)
        return snapshot.carpeta if snapshot else ""

    def get_responsable_movil(self, obj) -> str:
        emp = self._get_empleado_info(obj)
        if emp and emp.movil:
            return emp.movil
        snapshot = getattr(obj.actividad, "responsable_snapshot", None)
        return snapshot.movil if snapshot else ""

    def get_responsable_link_foto(self, obj) -> str:
        emp = self._get_empleado_info(obj)
        if emp and (emp.link_foto or emp.img):
            return emp.link_foto or emp.img or ""
        return ""


class AgendaGuardarSerializer(serializers.Serializer):
    """
    Serializador para crear o actualizar un agendamiento en `operaciones_agenda`.
    Soporta formato payload directo o diccionario data_form para retrocompatibilidad.
    """
    id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID del agendamiento si es una edición"
    )
    actividad_id = serializers.IntegerField(
        required=False,
        help_text="ID de la actividad/OT existente a agendar"
    )
    responsable_id = serializers.IntegerField(
        required=False,
        help_text="ID del técnico en auth_user"
    )
    fecha_inicio = serializers.DateField(
        required=False,
        help_text="Fecha de inicio (YYYY-MM-DD)"
    )
    fecha_fin = serializers.DateField(
        required=False,
        help_text="Fecha de fin (YYYY-MM-DD)"
    )
    sede = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Sede operativa (medellin, monteria, sincelejo, etc.)"
    )
    color_hex = serializers.CharField(
        max_length=7,
        required=False,
        default="#A55BD8",
        help_text="Color corporativo para la visualización en el calendario"
    )
    observacion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        default="",
        help_text="Observaciones adicionales"
    )
    estado = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Estado de la actividad (PENDIENTE, EN_PROCESO, etc.)"
    )
    tipo_trabajo = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Tipo de trabajo o nombre de la actividad"
    )
    descripcion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Descripción detallada de la actividad"
    )
    direccion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Dirección física de la actividad"
    )
    zona = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Zona o barrio"
    )
    nodo = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Nodo o central operativa"
    )
    latitud = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Coordenada Y"
    )
    longitud = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Coordenada X"
    )
    # Retrocompatibilidad para endpoints que envían objeto data_form
    data_form = serializers.DictField(
        required=False,
        help_text="Contenedor de datos formulario legacy"
    )
    data_param = serializers.DictField(
        required=False,
        default=dict
    )
    data_anterior = serializers.DictField(
        required=False,
        allow_null=True,
        default=None
    )




class AgendaParametrosCarpetaSaveSerializer(serializers.Serializer):
    sede = serializers.CharField(required=True)
    data_param = serializers.ListField(required=True)


class AgendaEliminarParametroSerializer(serializers.Serializer):
    sede = serializers.CharField(required=True)
    param_id = serializers.CharField(required=True)


class AgendaImportarCsvSerializer(serializers.Serializer):
    """
    Serializador para importar agendamientos masivos mediante archivo CSV.
    """
    file = serializers.FileField(
        required=True,
        help_text="Archivo CSV con columnas: ot, responsable_id, fecha_inicio, fecha_fin, sede, color_hex"
    )

    def validate_file(self, value):
        if not value.name.lower().endswith((".csv", ".txt")):
            raise serializers.ValidationError("El archivo debe ser un CSV válido.")
        return value
