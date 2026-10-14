"""
ParametrosService — fechas límite de cierre y jefes validadores (§5.8).

Reemplaza del legacy (base_salida_transporte.php):
- get_all_fecha (136) y guardar_permi_editar_fecha (198)  → cierres.
- upload_jefes_valid (469) e isUserLeaderOfSalida (782 / JS 1823) → jefes.

Nota cross-database (D-A10): empleados.Empleado vive en 'azul' (managed=False)
y en tests el router está desactivado. Por eso JAMÁS se usan JOINs hacia
Empleado (`empleado__cedula`, `select_related`) sino resolución en dos pasos:
1) cédula/pk → id contra Empleado (una query), 2) filtro local por `empleado_id`.
"""
from django.db import IntegrityError, transaction

from apps.empleados.models import Empleado

from ..models import FechaLimiteCierre, JefeValidador
from .periodos import entero, validar_mes, validar_periodo, validar_anio


class ParametrosService:
    """Única capa de reglas de parámetros del módulo transporte."""

    # ------------------------------------------------------------------ #
    # Fechas límite de cierre (B2 / D2)
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar_cierres(query_params=None):
        """Listado (legacy get_all_fecha: orden `fecha_limite` DESC).

        Filtros opcionales: mes, anio.
        """
        queryset = FechaLimiteCierre.objects.all()
        query_params = query_params or {}

        mes = query_params.get("mes")
        if mes not in (None, ""):
            mes = validar_mes(entero(mes, "mes"))
            queryset = queryset.filter(mes=mes)

        anio = query_params.get("anio")
        if anio not in (None, ""):
            anio = validar_anio(entero(anio, "anio"))
            queryset = queryset.filter(anio=anio)

        return queryset.order_by("-fecha_limite")

    @staticmethod
    def obtener_cierre(cierre_id):
        try:
            return FechaLimiteCierre.objects.get(pk=cierre_id)
        except FechaLimiteCierre.DoesNotExist:
            raise ValueError(
                f"No existe una fecha límite de cierre con id {cierre_id}."
            )

    @staticmethod
    def crear_cierre(datos, actor):
        """Alta de fecha límite; unicidad natural (mes, anio) — uq_cierre_mes_anio.

        El gate de permiso legacy ($permi_editar) se evalúa en la vista con
        DjangoModelPermissions (transporte.add/change_fecha_limitecierre).
        """
        mes, anio, fecha_limite = ParametrosService._validar_cierre(datos)

        if FechaLimiteCierre.objects.filter(mes=mes, anio=anio).exists():
            raise ValueError(
                f"Ya existe una fecha límite para {mes:02d}/{anio}."
            )

        try:
            with transaction.atomic():
                return FechaLimiteCierre.objects.create(
                    mes=mes,
                    anio=anio,
                    fecha_limite=fecha_limite,
                    creado_por=actor,
                )
        except IntegrityError:
            raise ValueError(
                f"Ya existe una fecha límite para {mes:02d}/{anio}."
            )

    @staticmethod
    def actualizar_cierre(cierre_id, datos, actor):
        """Actualización con snapshot: los campos ausentes conservan su valor
        (semántica estándar de PUT/PATCH en DRF; el serializer ya decide qué
        campos son obligatorios según el tipo de petición)."""
        cierre = ParametrosService.obtener_cierre(cierre_id)

        merged = {
            "mes": cierre.mes,
            "anio": cierre.anio,
            "fecha_limite": cierre.fecha_limite,
        }
        merged.update(datos)

        mes, anio, fecha_limite = ParametrosService._validar_cierre(merged)

        if (mes, anio) != (cierre.mes, cierre.anio):
            conflicto = (
                FechaLimiteCierre.objects.filter(mes=mes, anio=anio)
                .exclude(pk=cierre_id)
                .exists()
            )
            if conflicto:
                raise ValueError(
                    f"Ya existe una fecha límite para {mes:02d}/{anio}."
                )

        try:
            with transaction.atomic():
                cierre.mes = mes
                cierre.anio = anio
                cierre.fecha_limite = fecha_limite
                cierre.modificado_por = actor
                cierre.save()
        except IntegrityError:
            raise ValueError(
                f"Ya existe una fecha límite para {mes:02d}/{anio}."
            )
        return cierre

    @staticmethod
    def eliminar_cierre(cierre_id):
        """Borrado físico: la tabla no tiene dependientes (solo lectura
        en liquidaciones); el legacy no permitía borrar, Django sí (D2 CRUD)."""
        cierre = ParametrosService.obtener_cierre(cierre_id)
        cierre.delete()
        return cierre

    # ------------------------------------------------------------------ #
    # Jefes validadores (D1)
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar_jefes(query_params=None):
        """Listado de jefes con sus empleados resueltos en UNA query extra
        (in_bulk, sin JOIN cross-database). Devuelve lista ya paginable.

        Filtros opcionales: activo, empleado (pk).
        """
        queryset = JefeValidador.objects.all().order_by("id")
        query_params = query_params or {}

        activo = query_params.get("activo")
        if activo is not None and activo != "":
            queryset = queryset.filter(
                activo=str(activo).lower() in ("1", "true", "si")
            )

        empleado = query_params.get("empleado")
        if empleado not in (None, ""):
            queryset = queryset.filter(
                empleado_id=entero(empleado, "empleado")
            )

        jefes = list(queryset)
        ParametrosService._adjuntar_empleados(jefes)
        return jefes

    @staticmethod
    def obtener_jefe(jefe_id):
        try:
            jefe = JefeValidador.objects.get(pk=jefe_id)
        except JefeValidador.DoesNotExist:
            raise ValueError(f"No existe un jefe validador con id {jefe_id}.")
        ParametrosService._adjuntar_empleados([jefe])
        return jefe

    @staticmethod
    def crear_jefe(datos, actor):
        """Alta de jefe: un registro ACTIVO por empleado (el legacy guardaba
        un JSON donde las duplicaciones eran silenciosas)."""
        empleado_id = ParametrosService._validar_empleado(datos.get("empleado"))
        areas, carpetas = ParametrosService._validar_areas_carpetas(datos)

        if JefeValidador.objects.filter(
            empleado_id=empleado_id, activo=True
        ).exists():
            raise ValueError(
                "Ya existe un jefe validador activo para ese empleado."
            )

        try:
            with transaction.atomic():
                return JefeValidador.objects.create(
                    empleado_id=empleado_id,
                    areas=areas,
                    carpetas_por_area=carpetas,
                    activo=bool(datos.get("activo", True)),
                    creado_por=actor,
                )
        except IntegrityError:
            raise ValueError(
                "Ya existe un jefe validador activo para ese empleado."
            )

    @staticmethod
    def actualizar_jefe(jefe_id, datos, actor):
        """Actualización con snapshot: los campos ausentes conservan su valor
        (semántica estándar de PUT/PATCH en DRF; el serializer ya decide qué
        campos son obligatorios según el tipo de petición)."""
        jefe = ParametrosService.obtener_jefe(jefe_id)

        merged = {
            "empleado": jefe.empleado_id,
            "areas": jefe.areas,
            "carpetas_por_area": jefe.carpetas_por_area,
            "activo": jefe.activo,
        }
        merged.update(datos)

        empleado_id = ParametrosService._validar_empleado(merged.get("empleado"))
        areas, carpetas = ParametrosService._validar_areas_carpetas(merged)

        if merged.get("activo", True):
            duplicado = (
                JefeValidador.objects.filter(empleado_id=empleado_id, activo=True)
                .exclude(pk=jefe_id)
                .exists()
            )
            if duplicado:
                raise ValueError(
                    "Ya existe un jefe validador activo para ese empleado."
                )

        with transaction.atomic():
            jefe.empleado_id = empleado_id
            jefe.areas = areas
            jefe.carpetas_por_area = carpetas
            jefe.activo = bool(merged.get("activo", True))
            jefe.modificado_por = actor
            jefe.save()
        return jefe

    @staticmethod
    def inactivar_jefe(jefe_id, actor):
        """Baja lógica (como los demás maestros): nunca borrado físico."""
        jefe = ParametrosService.obtener_jefe(jefe_id)
        jefe.activo = False
        jefe.modificado_por = actor
        jefe.save(update_fields=["activo", "modificado_por", "modificado_en"])
        return jefe

    @staticmethod
    def es_jefe_validador(cedula, area, carpeta=None):
        """
        Réplica de isUserLeaderOfSalida (base_salida_transporte.php 782–796 y
        JS 1823–1839): jefe ACTIVO → su `areas` debe contener el área → si el
        área tiene carpetas listadas, la carpeta debe estar entre ellas
        (lista vacía = todas las carpetas del área).

        Devuelve bool. Resolución en dos pasos: cédula → id (query a
        empleados) y luego filtro local `empleado_id` (sin JOIN, D-A10).
        """
        if not cedula or not area:
            return False
        try:
            empleado_id = Empleado.objects.values_list("id", flat=True).get(
                cedula=str(cedula).strip()
            )
        except Empleado.DoesNotExist:
            return False

        for jefe in JefeValidador.objects.filter(
            empleado_id=empleado_id, activo=True
        ):
            if area not in (jefe.areas or []):
                continue
            carpetas = (jefe.carpetas_por_area or {}).get(area) or []
            if not carpetas:
                return True
            if carpeta is not None and carpeta in carpetas:
                return True
        return False

    # ------------------------------------------------------------------ #
    # Validaciones internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_cierre(datos):
        mes, anio = validar_periodo(datos.get("mes"), datos.get("anio"))
        fecha_limite = datos.get("fecha_limite")
        if not fecha_limite:
            raise ValueError("La fecha límite es obligatoria.")
        return mes, anio, fecha_limite

    @staticmethod
    def _validar_empleado(empleado):
        """Acepta instancia Empleado o pk; exige existencia (sin JOIN)."""
        if isinstance(empleado, Empleado):
            return empleado.pk
        if empleado in (None, ""):
            raise ValueError("El empleado es obligatorio.")
        empleado_id = entero(empleado, "empleado")
        if not Empleado.objects.filter(pk=empleado_id).exists():
            raise ValueError(f"No existe empleado con id {empleado_id}.")
        return empleado_id

    @staticmethod
    def _validar_areas_carpetas(datos):
        areas = datos.get("areas")
        if not isinstance(areas, list) or not areas:
            raise ValueError("Debe indicar al menos un área.")
        limpias = []
        for area in areas:
            if not isinstance(area, str) or not area.strip():
                raise ValueError("Cada área debe ser un texto no vacío.")
            limpias.append(area.strip())
        if len(set(limpias)) != len(limpias):
            raise ValueError("Hay áreas repetidas en la lista.")

        carpetas = datos.get("carpetas_por_area") or {}
        if not isinstance(carpetas, dict):
            raise ValueError(
                "carpetas_por_area debe ser un objeto {área: [carpetas]}."
            )
        for clave, valores in carpetas.items():
            if clave not in limpias:
                raise ValueError(
                    f"carpetas_por_area contiene el área '{clave}' "
                    "que no está en areas."
                )
            if not isinstance(valores, list) or any(
                not isinstance(carpeta, str) or not carpeta.strip()
                for carpeta in valores
            ):
                raise ValueError(
                    f"Las carpetas de '{clave}' deben ser una lista de textos."
                )
        return limpias, carpetas

    @staticmethod
    def _adjuntar_empleados(jefes):
        """Cachea `jefe.empleado` con una sola query (in_bulk) en lugar de
        N consultas o un JOIN imposible entre bases de datos."""
        ids = {jefe.empleado_id for jefe in jefes}
        if not ids:
            return
        empleados = Empleado.objects.in_bulk(ids)
        for jefe in jefes:
            empleado = empleados.get(jefe.empleado_id)
            if empleado is not None:
                # Asignación al cache del FK: posteriores lecturas no consultan.
                jefe.empleado = empleado
