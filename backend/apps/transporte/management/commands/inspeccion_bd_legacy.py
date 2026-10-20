"""
Inspección de SOLO LECTURA de las BDs legacy (gate G2 / Tramo C).

    manage.py inspeccion_bd_legacy [--exactas] [--alias azul default]

No escribe absolutamente nada: solo `SELECT`/`information_schema` contra
`azul` (bd_c3nc4s1s) y `default` (db_cincosas). Sirve para:

1. Confirmar conectividad ANTES de `migrate` (C1) y del ETL (C3).
2. Ver el estado real del esquema destino: ¿existen ya tablas
   `transporte_*`? ¿quedó algo a medias?
3. Dimensionar el ETL de C3 (conteo y columnas de las tablas legacy de
   salidas/conductores/vehículos).
4. Inventariar `programacion_parametros` (jefes, área/carpetas y las
   excepciones de ventana de días anteriores, `datos` en JSON).

`--exactas` cambia los conteos estimados de InnoDB por `COUNT(*)` exacto
(más lento en tablas grandes). El comando termina con estado 1 si alguna BD
no es accesible, para poder encadenarlo en scripts.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connections


# Subcadenas que nos interesan al listar el esquema legacy.
INTERES = (
    "transporte", "salida", "vehiculo", "conductor", "programacion",
    "personal", "agenda", "actividad", "festivo", "jefe",
)


class Command(BaseCommand):
    help = (
        "Inventario de solo lectura de azul/default: conectividad, tablas, "
        "conteos, columnas de las tablas del ETL y programacion_parametros."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--alias",
            nargs="*",
            default=["azul", "default"],
            help="Aliases a inspeccionar (por defecto: azul default).",
        )
        parser.add_argument(
            "--exactas",
            action="store_true",
            help="Conteos exactos con COUNT(*) en vez de TABLE_ROWS.",
        )

    # ------------------------------------------------------------------ #
    def handle(self, *args, **opciones):
        aliases = opciones["alias"]
        exactas = opciones["exactas"]
        accesibles = []

        self.stdout.write(self.style.MIGRATE_HEADING("=== 1. CONECTIVIDAD ==="))
        for alias in aliases:
            if self._conectar(alias):
                accesibles.append(alias)

        if not accesibles:
            raise CommandError(
                "Ninguna BD accesible: revisa la VPN/red (192.168.79.10)."
            )

        for alias in accesibles:
            self._inspeccionar(alias, exactas)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== FIN (solo lectura; no se escribió nada) ==="
        ))

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #
    def _conectar(self, alias) -> bool:
        cfg = connections[alias].settings_dict
        # Corto el cuelgue si la red no responde (mysqlclient: connect_timeout).
        cfg.setdefault("OPTIONS", {}).setdefault("connect_timeout", 5)
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT VERSION(), DATABASE()")
                version, base = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(
                f"  {alias:<8} OK  base={base}  MySQL={version}"
            ))
            return True
        except Exception as exc:  # noqa: BLE001 — informe, no crash
            self.stdout.write(self.style.ERROR(
                f"  {alias:<8} NO ACCESIBLE: {type(exc).__name__}: {str(exc)[:120]}"
            ))
            return False

    # ------------------------------------------------------------------ #
    # Esquema
    # ------------------------------------------------------------------ #
    def _inspeccionar(self, alias, exactas):
        esquema = connections[alias].settings_dict["NAME"]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n=== 2. ESQUEMA {alias} ({esquema}) ==="
        ))
        tablas = self._tablas(alias, esquema)
        self.stdout.write(f"  Total de tablas: {len(tablas)}")

        interesantes = [
            (nombre, filas) for nombre, filas in tablas
            if any(p in nombre.lower() for p in INTERES)
        ]
        if not interesantes:
            self.stdout.write("  (ninguna tabla coincide con el patrón del módulo)")
            return

        self.stdout.write("  Tablas de interés (filas estimadas InnoDB):")
        for nombre, filas in interesantes:
            extra = ""
            if exactas:
                extra = f"  [COUNT(*)={self._conteo_exacto(alias, nombre)}]"
            self.stdout.write(f"    {nombre:<45} {filas:>12}{extra}")
            columnas = self._columnas(alias, nombre)
            if columnas:
                self.stdout.write(f"        columnas: {', '.join(columnas)}")

        self._parametros(alias)

    def _tablas(self, alias, esquema):
        sql = (
            "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME"
        )
        return self._select(alias, sql, [esquema], por_defecto=[])

    def _columnas(self, alias, tabla):
        sql = (
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
            "ORDER BY ORDINAL_POSITION"
        )
        filas = self._select(alias, sql, [tabla], por_defecto=[])
        return [f[0] for f in filas]

    def _conteo_exacto(self, alias, tabla):
        # Identificador entrecomillado a mano: solo llega desde information_schema.
        resultado = self._select(
            alias, f"SELECT COUNT(*) FROM `{tabla}`", [], por_defecto=[None]
        )
        return resultado[0][0] if resultado else "?"

    def _parametros(self, alias):
        """Inventario de `programacion_parametros` (jefes/área/excepciones)."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== 3. programacion_parametros (url | condicion | bytes) ==="
        ))
        sql = (
            "SELECT url, condicion, CHAR_LENGTH(datos) "
            "FROM programacion_parametros ORDER BY url, condicion"
        )
        filas = self._select(alias, sql, [], por_defecto=None)
        if filas is None:
            self.stdout.write("  (tabla no disponible en este alias)")
            return
        for url, condicion, largo in filas:
            self.stdout.write(f"    {str(url):<32} {str(condicion):<44} {largo or 0:>8}")

    # ------------------------------------------------------------------ #
    def _select(self, alias, sql, params, por_defecto):
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as exc:  # noqa: BLE001 — tabla inexistente, etc.
            self.stdout.write(
                f"    (consulta no disponible en {alias}: "
                f"{type(exc).__name__}: {str(exc)[:80]})"
            )
            return por_defecto
