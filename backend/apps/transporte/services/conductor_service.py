"""
ConductorService — catálogo de conductores externos.

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §5.4.

Reglas de negocio:
- Unicidad de cédula (CR-3: auditar duplicados previos en la ETL).
- Edad DERIVADA de fecha_nacimiento, nunca persistida (corrige
  transporte_base_conductores.php líneas 454–458).
- Semáforo de vencimiento de licencia calculado en servidor.
- fecha_egreso solo se registra al inactivar el conductor.
- Auditoría de creación/modificación vía AuditoriaModel (D-A5).
"""
from datetime import date

from django.db import IntegrityError, transaction

from ..models import Conductor
from .vigencia import estado_vigencia


class ConductorService:
    """Única capa de reglas de negocio del catálogo de conductores."""

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar(query_params):
        """
        Listado con filtros opcionales: cedula, nombre, celular,
        tipo_vinculacion, activo ('true'/'false'), search (libre).
        """
        queryset = Conductor.objects.all()

        for param in ("cedula", "nombre_completo", "celular", "barrio"):
            value = query_params.get(param)
            if value:
                queryset = queryset.filter(**{f"{param}__icontains": value})

        tipo_vinculacion = query_params.get("tipo_vinculacion")
        if tipo_vinculacion:
            queryset = queryset.filter(tipo_vinculacion__iexact=tipo_vinculacion)

        activo = query_params.get("activo")
        if activo is not None and activo != "":
            queryset = queryset.filter(activo=str(activo).lower() in ("1", "true", "si"))

        search = query_params.get("search")
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(cedula__icontains=search)
                | Q(nombre_completo__icontains=search)
                | Q(celular__icontains=search)
            )

        return queryset.order_by("nombre_completo")

    @staticmethod
    def obtener(conductor_id):
        try:
            return Conductor.objects.get(pk=conductor_id)
        except Conductor.DoesNotExist:
            raise ValueError(f"No existe un conductor con id {conductor_id}.")

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @staticmethod
    def crear(datos, actor):
        """
        Alta de conductor. Exige fecha_ingreso; valida unicidad de cédula
        y coherencia de fechas antes de tocar la BD.
        """
        ConductorService._validar_fechas(datos)
        ConductorService._validar_cedula_unica(datos.get("cedula"))

        registros = ConductorService._sanear(datos)
        registros["creado_por"] = actor

        try:
            with transaction.atomic():
                return Conductor.objects.create(**registros)
        except IntegrityError:
            raise ValueError(
                "No se pudo crear el conductor: la cédula ya está registrada."
            )

    @staticmethod
    def actualizar(conductor_id, datos, actor, parche=False):
        """Actualización completa (parche=False) o por campos (parche=True)."""
        conductor = ConductorService.obtener(conductor_id)

        merged = {} if parche else ConductorService._datos_base(conductor)
        merged.update(datos)

        if "cedula" in merged:
            ConductorService._validar_cedula_unica(
                merged["cedula"], excluyendo=conductor_id
            )
        ConductorService._validar_fechas(merged, requiere_ingreso=not parche)

        registros = ConductorService._sanear(merged)
        registros["modificado_por"] = actor

        try:
            with transaction.atomic():
                for campo, valor in registros.items():
                    setattr(conductor, campo, valor)
                conductor.save()
        except IntegrityError:
            raise ValueError(
                "No se pudo actualizar el conductor: la cédula ya está registrada."
            )
        return conductor

    @staticmethod
    def inactivar(conductor_id, fecha_egreso, actor):
        """
        Baja lógica: activo=False + fecha_egreso obligatoria (§5.4).
        Nunca borrado físico: las salidas históricas lo referencian (PROTECT).
        """
        if not fecha_egreso:
            raise ValueError("La fecha de egreso es obligatoria al inactivar.")

        return ConductorService.actualizar(
            conductor_id,
            {"activo": False, "fecha_egreso": fecha_egreso},
            actor,
            parche=True,
        )

    # ------------------------------------------------------------------ #
    # Reglas de dominio (consultables por el ViewSet/serializer)
    # ------------------------------------------------------------------ #
    @staticmethod
    def calcular_edad(fecha_nacimiento, hoy=None):
        """Edad derivada; nunca se persiste (legacy la guardaba como texto)."""
        if not fecha_nacimiento:
            return None
        hoy = hoy or date.today()
        anios = hoy.year - fecha_nacimiento.year
        if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
            anios -= 1
        return anios

    @staticmethod
    def estado_licencia(licencia_vencimiento, hoy=None):
        """Semáforo en servidor (§5.4); delega en la regla compartida."""
        return estado_vigencia(licencia_vencimiento, hoy)

    # ------------------------------------------------------------------ #
    # Validaciones internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_cedula_unica(cedula, excluyendo=None):
        if not cedula:
            raise ValueError("La cédula es obligatoria.")
        queryset = Conductor.objects.filter(cedula=cedula)
        if excluyendo:
            queryset = queryset.exclude(pk=excluyendo)
        if queryset.exists():
            raise ValueError(f"Ya existe un conductor con la cédula {cedula}.")

    @staticmethod
    def _validar_fechas(datos, requiere_ingreso=True):
        ingreso = datos.get("fecha_ingreso")
        egreso = datos.get("fecha_egreso")
        nacimiento = datos.get("fecha_nacimiento")

        if requiere_ingreso and not ingreso:
            raise ValueError("La fecha de ingreso es obligatoria.")
        if ingreso and nacimiento and nacimiento > ingreso:
            raise ValueError(
                "La fecha de nacimiento no puede ser posterior a la fecha de ingreso."
            )
        if egreso and ingreso and egreso < ingreso:
            raise ValueError(
                "La fecha de egreso no puede ser anterior a la fecha de ingreso."
            )

    @staticmethod
    def _sanear(datos):
        """Copia solo campos del modelo y fuerza caja canónica (D-A6)."""
        campos = {f.name for f in Conductor._meta.fields}
        registros = {k: v for k, v in datos.items() if k in campos and k != "id"}
        if registros.get("tipo_vinculacion"):
            registros["tipo_vinculacion"] = registros["tipo_vinculacion"].upper()
        return registros

    @staticmethod
    def _datos_base(conductor):
        return {f.name: getattr(conductor, f.name) for f in Conductor._meta.fields}
