from apps.empleados.models import Empleado
from rest_framework.viewsets import ModelViewSet
from apps.empleados.serializers import EmpleadoSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework import filters
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes
from django.http import HttpResponse
from apps.empleados.services import EmpleadoService
from rest_framework.permissions import AllowAny


from rest_framework.parsers import JSONParser, FormParser, MultiPartParser


class EmpleadoViewSet(ModelViewSet):
    """
    ViewSet para gestionar empleados.
    
    Proporciona listar, crear, actualizar y eliminar empleados.
    Filtra automáticamente solo empleados activos.
    Soporta búsqueda en: cédula, nombre, apellido, cargo, móvil.
    
    Autenticación requerida: Token Bearer o API Key
    """
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    # Usa permisos por defecto: IsAuthenticatedOrAPIKey
    filter_backends = [filters.SearchFilter]
    search_fields = ['cedula', 'nombre', 'apellido', 'cargo', 'movil']

    def get_queryset(self):
        if self.action in ['retrieve', 'certificado_laboral', 'partial_update', 'update']:
            return EmpleadoService.listar({'estado': 'all'})
        
        request = getattr(self, 'request', None)
        if request is None:
            return EmpleadoService.listar({})
            
        query_params = getattr(request, 'query_params', getattr(request, 'GET', {}))
        return EmpleadoService.listar(query_params)

    @extend_schema(
        summary="Listar empleados activos",
        description="""
        Obtiene un listado de empleados con filtros avanzados.
        
        **Filtrado automático por estado:**
        - Si no envías `estado`, retorna solo empleados `ACTIVO`
        - Si envías `estado`, filtra por ese valor (`ACTIVO`, `INACTIVO`, `SUSPENDIDO`)
        
        **Parámetros de filtro disponibles:**
        - `search`: Búsqueda general en cédula, nombre, apellido, cargo, móvil
        - `cedula`, `nombre`, `apellido`, `area`, `carpeta`, `cargo`, `movil`
        - `supervisor`, `sede`, `codigo_sap`, `estado`
        
        **Campos incluidos:**
        - id, cédula, nombre, apellido, área, carpeta, cargo, móvil, estado, etc.
        """,
        tags=["empleados"],
        parameters=[
            OpenApiParameter(
                name='search',
                description='Búsqueda en cédula, nombre, apellido, cargo o móvil (búsqueda parcial, insensible a mayúsculas)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='cedula',
                description='Filtra por cédula (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='nombre',
                description='Filtra por nombre (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='apellido',
                description='Filtra por apellido (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='area',
                description='Filtra por área (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='carpeta',
                description='Filtra por carpeta (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='cargo',
                description='Filtra por cargo (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='movil',
                description='Filtra por móvil (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='supervisor',
                description='Filtra por supervisor (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='sede',
                description='Filtra por sede (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='codigo_sap',
                description='Filtra por código SAP (búsqueda parcial)',
                required=False,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='estado',
                description='Filtra por estado. Valores: ACTIVO, INACTIVO, SUSPENDIDO',
                required=False,
                type=OpenApiTypes.STR,
                enum=['ACTIVO', 'INACTIVO', 'SUSPENDIDO']
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Lista empleados activos con búsqueda"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Crear un nuevo empleado",
        description="""
        Crea un nuevo empleado.
        
        **Campos requeridos:**
        - cedula: Cédula única
        - nombre: Nombre del empleado
        - apellido: Apellido del empleado
        - cargo: Cargo del empleado
        - area: Área a la que pertenece
        - carpeta: Carpeta asignada
        - movil: Número de móvil
        
        **Campos opcionales:**
        - estado: Estado del empleado (por defecto ACTIVO)
        - email: Correo electrónico
        """,
        tags=["empleados"],
    )
    def create(self, request, *args, **kwargs):
        """Crear un nuevo empleado"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Obtener detalles de un empleado",
        description="Obtiene toda la información de un empleado específico",
        tags=["empleados"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Obtener detalles de un empleado"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Actualizar un empleado completamente",
        description="Actualiza todos los campos de un empleado. Se requieren todos los campos requeridos.",
        tags=["empleados"],
    )
    def update(self, request, *args, **kwargs):
        """Actualizar un empleado completamente"""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Actualizar parcialmente un empleado",
        description="Actualiza solo los campos proporcionados de un empleado.",
        tags=["empleados"],
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualizar parcialmente un empleado"""
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Eliminar un empleado",
        description="""
        Realiza soft delete por defecto cambiando `estado` a `INACTIVO`.

        **Eliminación física (caso específico):**
        - Enviar `?hard_delete=true`
        - Requiere una cuenta administradora (`is_superuser`)
        """,
        tags=["empleados"],
        parameters=[
            OpenApiParameter(
                name='hard_delete',
                description='Si es true y la cuenta es superusuaria, elimina físicamente el registro',
                required=False,
                type=OpenApiTypes.BOOL
            ),
        ]
    )
    def destroy(self, request, *args, **kwargs):
        """Eliminar un empleado (soft delete por defecto)"""
        instance = self.get_object()

        hard_delete = str(request.query_params.get('hard_delete', '')).lower() in ('1', 'true', 'yes')
        was_deleted = EmpleadoService.eliminar(
            instance,
            actor_user=request.user,
            hard_delete=hard_delete,
        )

        if not was_deleted:
            return Response(
                {'detail': 'No tienes permisos para eliminación física.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Generar certificado laboral en PDF",
        description="""
        Genera un certificado laboral en PDF a partir de la información del empleado y
        del complemento en `cinco_base_de_personal_siigo`.

        **Fuente principal de datos:**
        - `cinco_base_de_personal`: nombre, cédula, cargo base, fecha ingreso
        - `cinco_base_de_personal_siigo`: salario, tipo contrato, cargo SIIGO y extras JSON

        **Parámetros opcionales:**
        - `document_type`: fuerza el tipo de documento (`CC`, `PT`, `TI`, `CE`)
        """,
        tags=["empleados"],
        parameters=[
            OpenApiParameter(
                name="document_type",
                description="Tipo de documento a marcar en el certificado",
                required=False,
                type=OpenApiTypes.STR,
                enum=["CC", "PT", "TI", "CE"],
            ),
        ],
        responses={
            (200, "application/pdf"): OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Archivo PDF del certificado laboral.",
            ),
        },
    )
    @action(detail=True, methods=["get", "post"], url_path="certificado-laboral")
    def certificado_laboral(self, request, *args, **kwargs):
        instance = self.get_object()
        params = request.data if request.method == "POST" else request.query_params
        document_type = params.get("document_type", "")
        
        manual_data = {
            "salario": params.get("salario"),
            "tipo_contrato": params.get("tipo_contrato"),
            "cargo": params.get("cargo"),
            "fecha_ingreso": params.get("fecha_ingreso"),
            "fecha_egreso": params.get("fecha_egreso"),
            "estado": params.get("estado"),
        }
        manual_data = {k: v for k, v in manual_data.items() if v not in (None, "")}

        try:
            result = EmpleadoService.generar_certificado_laboral(
                empleado=instance,
                document_type=document_type,
                manual_data=manual_data,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "requires_manual_input": True},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError as exc:
            detail = str(exc)
            if detail == "reportlab_no_instalado":
                return Response(
                    {"detail": "El servidor no tiene instalada la dependencia para generar PDF."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            raise

        response = HttpResponse(result["content"], content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{result["filename"]}"'
        return response

    @action(detail=False, methods=["get"], url_path="certificado-config")
    def get_certificado_config(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
            
        from apps.security.models import CertificadoFirmaConfig
        config = CertificadoFirmaConfig.objects.first()
        
        firmante_nombre = config.firmante_nombre if config else "FARAY MONSALVE URREGO"
        firmante_cargo = config.firmante_cargo if config else "Dirección Gestión Humana"
        firma_imagen_nombre = config.firma_imagen_nombre if config else "Firma-RRHH.png"
        
        can_edit = _is_admin_or_programacion(request.user)
        
        return Response({
            "firmante_nombre": firmante_nombre,
            "firmante_cargo": firmante_cargo,
            "firma_imagen_nombre": firma_imagen_nombre,
            "can_edit": can_edit
        })

    @action(detail=False, methods=["post"], url_path="certificado-config/update")
    def update_certificado_config(self, request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not _is_admin_or_programacion(request.user):
            return Response({"detail": "No tiene permisos para modificar el firmante de los certificados"}, status=status.HTTP_403_FORBIDDEN)
            
        firmante_nombre = request.data.get("firmante_nombre")
        firmante_cargo = request.data.get("firmante_cargo")
        firma_imagen = request.FILES.get("firma_imagen")
        
        if not firmante_nombre or not firmante_cargo:
            return Response({"detail": "El nombre y el cargo son requeridos"}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.security.models import CertificadoFirmaConfig
        config = CertificadoFirmaConfig.objects.first()
        if not config:
            config = CertificadoFirmaConfig()
            
        config.firmante_nombre = firmante_nombre.strip()
        config.firmante_cargo = firmante_cargo.strip()
        
        if firma_imagen:
            import os
            from django.core.files.storage import FileSystemStorage
            from django.utils.text import get_valid_filename
            
            filename = get_valid_filename(firma_imagen.name)
            
            # Guardar en directorio local
            local_dir = EmpleadoService.LOCAL_IMAGE_DIR
            local_dir.mkdir(parents=True, exist_ok=True)
            
            # Intentar eliminar la firma anterior si era personalizada para no acumular basura
            old_filename = config.firma_imagen_nombre
            server_dir = EmpleadoService.SERVER_IMAGE_DIR
            if old_filename and old_filename not in ["Firma-RRHH.png", "firma-rrhh.png", "firma_rrhh.png"]:
                old_local_path = local_dir / old_filename
                if old_local_path.exists():
                    try:
                        old_local_path.unlink()
                    except Exception:
                        pass
                if server_dir.exists():
                    old_server_path = server_dir / old_filename
                    if old_server_path.exists():
                        try:
                            old_server_path.unlink()
                        except Exception:
                            pass
            
            local_file_path = local_dir / filename
            if local_file_path.exists():
                try:
                    local_file_path.unlink()
                except Exception:
                    pass
                    
            fs_local = FileSystemStorage(location=str(local_dir))
            saved_filename = fs_local.save(filename, firma_imagen)
            
            # Guardar en directorio servidor si existe
            if server_dir.exists():
                try:
                    server_dir.mkdir(parents=True, exist_ok=True)
                    server_file_path = server_dir / saved_filename
                    if server_file_path.exists():
                        try:
                            server_file_path.unlink()
                        except Exception:
                            pass
                    
                    fs_server = FileSystemStorage(location=str(server_dir))
                    firma_imagen.seek(0)
                    fs_server.save(saved_filename, firma_imagen)
                except Exception:
                    pass
                    
            config.firma_imagen_nombre = saved_filename
            
        config.save()
        
        return Response({
            "firmante_nombre": config.firmante_nombre,
            "firmante_cargo": config.firmante_cargo,
            "firma_imagen_nombre": config.firma_imagen_nombre,
            "can_edit": True
        })

    @action(detail=False, methods=["get"], url_path="certificado-firma-imagen", permission_classes=[AllowAny])
    def get_certificado_firma_imagen(self, request, *args, **kwargs):
        from apps.security.models import CertificadoFirmaConfig
        config = CertificadoFirmaConfig.objects.first()
        filename = config.firma_imagen_nombre if config else "Firma-RRHH.png"
        
        path = EmpleadoService._resolve_certificate_image_path(filename)
        if not path or not path.exists():
            from django.http import Http404
            raise Http404("Firma no encontrada")
            
        from django.http import FileResponse
        content_type = "image/png"
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            content_type = "image/jpeg"
            
        response = FileResponse(open(path, "rb"), content_type=content_type)
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        return response


def _is_admin_or_programacion(user):
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    try:
        from apps.empleados.models import Empleado
        from django.db.models import Q
        empleado = Empleado.objects.filter(Q(cedula=user.username) | Q(id=user.id)).first()
        if empleado:
            area = (empleado.area or "").strip().upper()
            carpeta = (empleado.carpeta or "").strip().upper()
            if "PROGRAMACION" in area or "ADMIN" in area or "PROGRAMACION" in carpeta or "ADMIN" in carpeta:
                return True
    except Exception:
        pass
    return False
