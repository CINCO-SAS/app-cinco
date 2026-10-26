# backend/apps/transporte/management/commands/seed_gate_verificacion.py
"""
Seeds de VERIFICACIÓN del gate de acceso al módulo (menú + Programación).

Crea 3 usuarios de prueba (auth_user en la BD default) con sus filas
correspondientes en `cinco_base_de_personal` (BD azul, id = user.id)
para verificar en navegador las3 ramas del gate 2026-10-26:

  999991 · PRUEBA GATE / POR MENU          → entra por menú (leer)
  999992 · PRUEBA GATE / POR PROGRAMACION  → entra por área PROGRAMACION
  999993 · PRUEBA GATE / SIN ACCESO        → NO entra (debe dar 403)

Contraseña de los tres: PruebaGate2026*

Uso:
  manage.py seed_gate_verificacion                    # crea/actualiza + verifica
  manage.py seed_gate_verificacion --diagnosticar 123  # diagnóstico SOLO LECTURA de una cédula real
  manage.py seed_gate_verificacion --limpiar          # borra los3 seeds

Idempotente (update-or-create). Los seeds usan cédulas 99999x y nombres
marcados con "PRUEBA GATE" para que sean fáciles de identificar en reportes.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connections

from apps.transporte.views.permisos import PuedeVerModuloTransporte

MENUS_TRANSPORTE = (
    "transporte_salida.php;base_salida_transporte.php;"
    "transporte_base_conductores.php;transporte_reporte_salida_daria.php"
)

SEEDS = [
    {
        "cedula": "999991",
        "apellido": "POR MENU",
        "area": "",
        "leer": MENUS_TRANSPORTE,
        "espera": "ENTRA (menú)",
    },
    {
        "cedula": "999992",
        "apellido": "POR PROGRAMACION",
        "area": "PROGRAMACION",
        "leer": "",
        "espera": "ENTRA (área Programación)",
    },
    {
        "cedula": "999993",
        "apellido": "SIN ACCESO",
        "area": "",
        "leer": "",
        "espera": "NO ENTRA (403)",
    },
]

CLAVE = "PruebaGate2026*"


class Command(BaseCommand):
    help = "Seeds de verificación del gate de acceso (menú + Programación)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Elimina los3 usuarios seed y sus filas en la BD azul.",
        )
        parser.add_argument(
            "--diagnosticar",
            metavar="CEDULA",
            help="Diagnóstico SOLO LECTURA de una cédula existente "
            "(muestra leer/área y si el gate la deja entrar).",
        )

    # ------------------------------------------------------------------ #
    def handle(self, *args, **kwargs):
        if kwargs["limpiar"]:
            self._limpiar()
        elif kwargs["diagnosticar"]:
            self._diagnosticar(kwargs["diagnosticar"])
        else:
            self._sembrar()
            self._verificar()

    # ------------------------------------------------------------------ #
    def _sembrar(self):
        for s in SEEDS:
            user, _ = User.objects.update_or_create(
                username=s["cedula"],
                defaults={
                    "first_name": "PRUEBA GATE",
                    "last_name": s["apellido"],
                    "is_active": True,
                    "is_superuser": False,
                },
            )
            user.set_password(CLAVE)
            user.save()

            with connections["azul"].cursor() as c:
                # La fila legacy DEBE llevar id = user.id (así la lee el
                # gate y el sidebar). sql_mode vacío ⇒ los NO NULL no
                # listados reciben defaults implícitos.
                c.execute(
                    """
                    INSERT INTO cinco_base_de_personal
                        (id, cedula, nombre, apellido, area, leer,
                         insertar, editar, importar, manual, admin, exportar)
                    VALUES (%s, %s, %s, %s, %s, %s,
                            '', '', '', '', '', '')
                    ON DUPLICATE KEY UPDATE
                        id = VALUES(id), nombre = VALUES(nombre),
                        apellido = VALUES(apellido), area = VALUES(area),
                        leer = VALUES(leer)
                    """,
                    [
                        user.id,
                        s["cedula"],
                        "PRUEBA GATE",
                        s["apellido"],
                        s["area"],
                        s["leer"],
                    ],
                )
            self.stdout.write(
                f"  seed {s['cedula']} ({s['apellido']}) → user.id={user.id} OK"
            )

    def _verificar(self):
        self.stdout.write("")
        self.stdout.write("=== VERIFICACIÓN DEL GATE (misma lógica que la vista) ===")
        todo_ok = True
        for s in SEEDS:
            user = User.objects.get(username=s["cedula"])
            permite = PuedeVerModuloTransporte().has_permission(
                type("Req", (), {"user": user})(), None
            )
            visto = "ENTRA" if permite else "NO ENTRA"
            ok = visto in s["espera"]
            todo_ok = todo_ok and ok
            marca = "OK " if ok else "!! "
            self.stdout.write(
                f"  {marca}{s['cedula']} · {s['apellido']:<18} → "
                f"{visto:<8} (esperado: {s['espera']})"
            )
        self.stdout.write("")
        self.stdout.write(
            f"Contraseña de los3 seeds: {CLAVE}"
        )
        self.stdout.write(
            "Limpieza posterior: manage.py seed_gate_verificacion --limpiar"
        )
        if not todo_ok:
            self.stdout.write(self.style.ERROR("Hay seeds que no dan lo esperado."))

    # ------------------------------------------------------------------ #
    def _limpiar(self):
        cedulas = [s["cedula"] for s in SEEDS]
        with connections["azul"].cursor() as c:
            c.execute(
                "DELETE FROM cinco_base_de_personal WHERE cedula IN (%s,%s,%s)",
                cedulas,
            )
            borradas_azul = c.rowcount
        borrados_auth = User.objects.filter(username__in=cedulas).delete()
        self.stdout.write(
            f"  filas eliminadas en azul: {borradas_azul}; "
            f"usuarios auth: {borrados_auth}"
        )

    # ------------------------------------------------------------------ #
    def _diagnosticar(self, cedula):
        """Solo lectura: por qué una cédula entra o no al módulo."""
        try:
            user = User.objects.get(username=str(cedula))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No existe auth_user {cedula}."))
            return
        self.stdout.write(f"user.id={user.id} super={user.is_superuser}")

        menus = []
        with connections["azul"].cursor() as c:
            c.execute(
                "SELECT id, url FROM config_menu "
                "WHERE estado='ACTIVO' AND url LIKE %s",
                ["%transporte%"],
            )
            menus = c.fetchall()
            for mid, url in menus:
                c.execute(
                    "SELECT leer FROM cinco_base_de_personal WHERE id = %s",
                    [user.id],
                )
                fila = c.fetchone()
                tiene = fila and url in (fila[0] or "")
                self.stdout.write(
                    f"  menú {mid} {url:<45} leer: "
                    f"{'SÍ' if tiene else 'no'}"
                )
            c.execute(
                "SELECT area FROM cinco_base_de_personal WHERE id = %s",
                [user.id],
            )
            fila = c.fetchone()
            area = fila[0] if fila else None
            self.stdout.write(f"  área en cinco_base_de_personal: {area!r}")

        permite = PuedeVerModuloTransporte().has_permission(
            type("Req", (), {"user": user})(), None
        )
        self.stdout.write(
            "RESULTADO: "
            + ("ENTRA al módulo" if permite else "NO entra (403)")
        )
