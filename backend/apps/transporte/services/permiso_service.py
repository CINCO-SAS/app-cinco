"""
PermisoService — única capa de permisos del módulo (CR-8 / §5.9).

Reemplaza las cédulas y flags hardcodeados del legacy (PHP/JS) por
grupos y permisos Django. Mapping (§5.9):

======================================  =============================
Cédula / marca legacy                   Permiso Django
======================================  =============================
cédulas admin hardcodeadas (PHP)        grupo ``transporte_admin``
``$permi_programacion``                 permiso ``puede_programar``
``permi_especial`` (1000756621)         permiso ``permiso_especial``
``permi_editar_fecha`` (cédula oculta)  permiso ``editar_tras_cierre``
pestaña Datos ``_fix`` (1055837370)     sin bifurcación; por funcionalidad
perfil carpeta TRANSPORTE               grupo ``transporte_operador``
======================================  =============================

Los tres permisos se declaran en ``Salida.Meta.permissions`` (migración
0006). El servicio solo LEE permisos; el alta de usuarios en grupos y la
concesión de permisos es tarea de administración, no del módulo.
"""
from django.contrib.auth.models import AnonymousUser

GRUPO_ADMIN = "transporte_admin"
GRUPO_OPERADOR = "transporte_operador"

PERMISO_PROGRAMAR = "transporte.puede_programar"
PERMISO_ESPECIAL = "transporte.permiso_especial"
PERMISO_EDITAR_TRAS_CIERRE = "transporte.editar_tras_cierre"


class PermisoService:
    """Única capa de reglas de permisos (CR-8). Ninguna vista hardcodea cédulas."""

    @staticmethod
    def _autenticado(user):
        return bool(
            user is not None
            and not isinstance(user, AnonymousUser)
            and getattr(user, "is_authenticated", False)
        )

    @staticmethod
    def _en_grupo(user, nombre):
        if not PermisoService._autenticado(user):
            return False
        return user.groups.filter(name=nombre).exists()

    # ------------------------------------------------------------------ #
    # Cédulas legacy → permisos / grupos
    # ------------------------------------------------------------------ #
    @staticmethod
    def es_admin(user):
        """cédulas admin del PHP → grupo ``transporte_admin`` (+ superuser)."""
        if not PermisoService._autenticado(user):
            return False
        if getattr(user, "is_superuser", False):
            return True
        return PermisoService._en_grupo(user, GRUPO_ADMIN)

    @classmethod
    def puede_programar(cls, user):
        """``$permi_programacion`` → permiso ``puede_programar`` (o admin)."""
        if not cls._autenticado(user):
            return False
        # Paridad con el comportamiento productivo: staff también programa.
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        if user.has_perm(PERMISO_PROGRAMAR):
            return True
        return cls.es_admin(user)

    @classmethod
    def permiso_especial(cls, user):
        """``permi_especial`` (1000756621) → permiso ``permiso_especial``."""
        if not cls._autenticado(user):
            return False
        if cls.es_admin(user):
            return True
        return user.has_perm(PERMISO_ESPECIAL)

    @classmethod
    def puede_editar_tras_cierre(cls, user):
        """``permi_editar_fecha`` (cédula oculta) → permiso ``editar_tras_cierre``."""
        if not cls._autenticado(user):
            return False
        if cls.es_admin(user):
            return True
        return user.has_perm(PERMISO_EDITAR_TRAS_CIERRE)

    @staticmethod
    def es_operador(user):
        """perfil carpeta TRANSPORTE → grupo ``transporte_operador``."""
        return PermisoService._en_grupo(user, GRUPO_OPERADOR)

    # ------------------------------------------------------------------ #
    # Snapshot para GET /permisos/estado/
    # ------------------------------------------------------------------ #
    @classmethod
    def estado(cls, user):
        """
        Estado de permisos del usuario para el frontend (reemplaza las
        constantes JS ``permi_especial``/``permi_editar_fecha``/
        ``isPerfilTransporte``/``isProgram`` que el PHP quemaba por cédula).

        Incluye el detalle de jefatura (áreas/carpetas) cuando el usuario
        es jefe validador, reutilizando ``ParametrosService``.
        """
        from ..models import JefeValidador
        from ..services import ParametrosService

        if not cls._autenticado(user):
            return {
                "autenticado": False,
                "username": "",
                "es_admin": False,
                "es_operador": False,
                "puede_programar": False,
                "permiso_especial": False,
                "editar_tras_cierre": False,
                "es_jefe": False,
                "areas_jefe": [],
            }

        cedula = str(getattr(user, "username", "") or "").strip()
        jefes = ParametrosService.jefes_de_cedula(cedula) if cedula else []
        areas = sorted(
            {a for j in jefes for a in (j.get("areas") or [])}
        )
        return {
            "autenticado": True,
            "username": cedula,
            "es_admin": cls.es_admin(user),
            "es_operador": cls.es_operador(user),
            "puede_programar": cls.puede_programar(user),
            "permiso_especial": cls.permiso_especial(user),
            "editar_tras_cierre": cls.puede_editar_tras_cierre(user),
            "es_jefe": bool(jefes),
            "areas_jefe": areas,
        }
