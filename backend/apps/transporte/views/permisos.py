"""
Permisos del módulo Transporte.

2026-10-26: el gate `DjangoModelPermissions` (permisos de modelo Django)
se sustituyó por este check de MENÚ + ÁREA, por decisión de los
programadores del módulo:

- **Quien puede VER el módulo Transporte en su menú puede entrar y
  operarlo.** La visibilidad del menú vive en la BD azul: `config_menu`
  (filas legacy `.php` del módulo) contra `cinco_base_de_personal.leer`,
  exactamente el mismo cálculo que usa el sidebar.
- **Programación también puede entrar**, aunque no tenga el menú
  asignado: es el área que despacha la flota (`cinco_base_de_personal.
  area = 'PROGRAMACION'`).
"""
from django.db import connections
from rest_framework.permissions import BasePermission

from apps.common.models import ConfigMenu


class PuedeVerModuloTransporte(BasePermission):
    """
    True si el usuario autenticado:

    1. tiene `leer` en ALGÚN menú activo del módulo Transporte
       (`config_menu` en la BD azul), o
    2. pertenece al área PROGRAMACION (`cinco_base_de_personal.area`).

    Superusuarios pasan siempre. Si la BD de menús no está disponible
    (entorno de pruebas SQLite, donde `config_menu` no existe), el gate
    se degrada a solo exigir autenticación para no romper la suite.
    """

    message = "No tiene permiso para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        # 1) Visibilidad del módulo en el menú (cálculo del sidebar).
        try:
            menus = ConfigMenu.objects.using("azul").filter(
                estado="ACTIVO", url__icontains="transporte"
            )
            if any(
                menu.get_permissions_for_user(user, menu.url).get("read", False)
                for menu in menus
            ):
                return True
        except Exception:
            # Sin tabla de menú (pruebas en SQLite): solo autenticación.
            return True

        # 2) Área Programación: opera el módulo sin necesitar el menú.
        try:
            with connections["azul"].cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM cinco_base_de_personal "
                    "WHERE id = %s AND UPPER(area) = 'PROGRAMACION' "
                    "LIMIT 1",
                    [user.id],
                )
                return cursor.fetchone() is not None
        except Exception:
            # Sin tabla legacy: no se puede confirmar el área ⇒ se niega
            # (ya falló también la vía de menú).
            return False
