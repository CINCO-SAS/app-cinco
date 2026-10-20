"""
C2 — Auditoría de los datos legacy en `azul` (solo lectura).

    manage.py auditar_datos_legacy [--alias azul] [--top 20]

Responde al §7.1 del consolidado (CR-3, CR-1, CR-2, D-A12): antes de
cargar el ETL y antes de crear constraints UNIQUE, hay que saber si los
datos legacy los soportan. No escribe absolutamente nada.

Qué verifica:
- **CR-3** unicidad de `placa` (vehículos) y de `cedula` (conductores y
  personal), con el detalle de los duplicados.
- **CR-1** salidas (vehículo, día) repetidas con estado vivo
  (`estado != 'ELIMINADO'`) -> decide si el UNIQUE parcial sobrevive.
- **CR-2** salidas (móvil, día) repetidas excluyendo las sentinelas
  `'disponible'` / `'0'` (que no son un móvil real).
- Integridad referencial: salidas con `id_vehiculo` o `cedula_tecnico`
  que no existen en sus catálogos (huérfanos que el ETL debe resolver).
- Cobertura de área/carpeta del personal, que CR-3 exige para despachar.

Sale con estado 2 si encuentra duplicados duros (placa/cédula), para que
el pipeline del cutover no avance sobre datos descuadrados.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

# Tablas legacy en `azul` (nombres PHP, no Django).
TABLA_VEHICULOS = "transportadores_vehiculos"
TABLA_CONDUCTORES = "transporte_base_conductores"
TABLA_SALIDAS = "transporte_registro_salida"
TABLA_PERSONAL = "cinco_base_de_personal"

# Sentinelas que el legacy escribía en `movil_sale` sin ser un móvil real.
SENTINELAS_MOVIL = ("disponible", "0")


class Command(BaseCommand):
    help = (
        "Auditoría de solo lectura de los datos legacy (CR-3/CR-1/CR-2): "
        "duplicados de placa/cédula, colisiones de unicidad parcial de "
        "salidas y huérfanos del ETL."
    )

    def add_arguments(self, parser):
        parser.add_argument("--alias", default="azul", help="Alias BD legacy.")
        parser.add_argument(
            "--top", type=int, default=20, help="Filas de detalle a mostrar."
        )

    # ------------------------------------------------------------------ #
    def handle(self, *args, **opciones):
        self.alias = opciones["alias"]
        self.top = opciones["top"]
        self.hallazgos_duros = 0

        try:
            with connections[self.alias].cursor() as cursor:
                cursor.execute("SELECT DATABASE(), VERSION()")
                base, version = cursor.fetchone()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                f"BD '{self.alias}' no accesible: {type(exc).__name__}: {exc}"
            )

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== AUDITORÍA LEGACY (solo lectura) — {base} · MySQL {version} ==="
        ))

        self._vehiculos()
        self._conductores()
        self._personal()
        self._salidas()
        self._integridad()

        if self.hallazgos_duros:
            self.stdout.write(self.style.ERROR(
                f"\n{self.hallazgos_duros} hallazgo(s) duro(s): resolver ANTES del "
                "ETL (deduplicación CR-3)."
            ))
            raise SystemExit(2)
        self.stdout.write(self.style.SUCCESS(
            "\nSin duplicados duros: los constraints UNIQUE pueden crearse."
        ))

    # ------------------------------------------------------------------ #
    def _consulta(self, sql, params=None):
        with connections[self.alias].cursor() as cursor:
            cursor.execute(sql, params or [])
            return cursor.fetchall()

    def _escalar(self, sql, params=None):
        filas = self._consulta(sql, params)
        return filas[0][0] if filas else None

    def _encabezado(self, texto):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {texto} ==="))

    # ------------------------------------------------------------------ #
    # CR-3 · vehículos
    # ------------------------------------------------------------------ #
    def _vehiculos(self):
        self._encabezado(f"CR-3 · VEHÍCULOS ({TABLA_VEHICULOS})")
        total = self._escalar(f"SELECT COUNT(*) FROM `{TABLA_VEHICULOS}`")
        distintas = self._escalar(
            f"SELECT COUNT(DISTINCT TRIM(UPPER(placa))) FROM `{TABLA_VEHICULOS}` "
            "WHERE placa IS NOT NULL AND TRIM(placa) <> ''"
        )
        vacias = self._escalar(
            f"SELECT COUNT(*) FROM `{TABLA_VEHICULOS}` "
            "WHERE placa IS NULL OR TRIM(placa) = ''"
        )
        self.stdout.write(f"  Filas: {total}   Placas distintas: {distintas}   "
                          f"Sin placa: {vacias}")

        duplicadas = self._consulta(
            f"SELECT TRIM(UPPER(placa)) AS placa, COUNT(*) AS n, "
            f"GROUP_CONCAT(id ORDER BY id) "
            f"FROM `{TABLA_VEHICULOS}` "
            "WHERE placa IS NOT NULL AND TRIM(placa) <> '' "
            "GROUP BY placa HAVING n > 1 ORDER BY n DESC"
        )
        if not duplicadas:
            self.stdout.write(self.style.SUCCESS("  [OK] Placa única (no hay duplicados)."))
            return
        self.hallazgos_duros += len(duplicadas)
        self.stdout.write(self.style.ERROR(
            f"  [!!] {len(duplicadas)} placa(s) duplicada(s) — deduplicar antes del ETL:"
        ))
        for placa, n, ids in duplicadas[: self.top]:
            self.stdout.write(f"      {placa:<12} x{n:<4} ids: {ids}")

    # ------------------------------------------------------------------ #
    # CR-3 · conductores
    # ------------------------------------------------------------------ #
    def _conductores(self):
        self._encabezado(f"CR-3 · CONDUCTORES ({TABLA_CONDUCTORES})")
        total = self._escalar(f"SELECT COUNT(*) FROM `{TABLA_CONDUCTORES}`")
        distintas = self._escalar(
            f"SELECT COUNT(DISTINCT TRIM(cedula)) FROM `{TABLA_CONDUCTORES}` "
            "WHERE cedula IS NOT NULL AND TRIM(cedula) <> ''"
        )
        self.stdout.write(f"  Filas: {total}   Cédulas distintas: {distintas}")
        duplicadas = self._consulta(
            "SELECT TRIM(cedula), COUNT(*), GROUP_CONCAT(id ORDER BY id) "
            f"FROM `{TABLA_CONDUCTORES}` "
            "WHERE cedula IS NOT NULL AND TRIM(cedula) <> '' "
            "GROUP BY cedula HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC"
        )
        if not duplicadas:
            self.stdout.write(self.style.SUCCESS("  [OK] Cédula única."))
            return
        self.hallazgos_duros += len(duplicadas)
        self.stdout.write(self.style.ERROR(
            f"  [!!] {len(duplicadas)} cédula(s) de conductor duplicada(s):"
        ))
        for cedula, n, ids in duplicadas[: self.top]:
            self.stdout.write(f"      {cedula:<14} x{n:<4} ids: {ids}")

    # ------------------------------------------------------------------ #
    # Personal (área/carpeta que CR-3 exige para despachar)
    # ------------------------------------------------------------------ #
    def _personal(self):
        self._encabezado(f"PERSONAL ({TABLA_PERSONAL})")
        total = self._escalar(f"SELECT COUNT(*) FROM `{TABLA_PERSONAL}`")
        con_area = self._escalar(
            f"SELECT COUNT(*) FROM `{TABLA_PERSONAL}` "
            "WHERE area IS NOT NULL AND TRIM(area) <> ''"
        )
        con_carpeta = self._escalar(
            f"SELECT COUNT(*) FROM `{TABLA_PERSONAL}` "
            "WHERE carpeta IS NOT NULL AND TRIM(carpeta) <> ''"
        )
        con_ambos = self._escalar(
            f"SELECT COUNT(*) FROM `{TABLA_PERSONAL}` "
            "WHERE area IS NOT NULL AND TRIM(area) <> '' "
            "AND carpeta IS NOT NULL AND TRIM(carpeta) <> ''"
        )
        self.stdout.write(
            f"  Filas: {total}   con área: {con_area}   "
            f"con carpeta: {con_carpeta}   con ambas: {con_ambos}\n"
            f"  -> {total - con_ambos} empleado(s) sin área+carpeta: no podrán "
            "despachar (regla de servicio CR-3)."
        )
        self.stdout.write("  Áreas distintas en uso:")
        for area, n in self._consulta(
            f"SELECT TRIM(area) AS a, COUNT(*) FROM `{TABLA_PERSONAL}` "
            "WHERE area IS NOT NULL AND TRIM(area) <> '' "
            "GROUP BY a ORDER BY COUNT(*) DESC"
        )[:15]:
            self.stdout.write(f"      {str(area):<20} {n:>6}")

    # ------------------------------------------------------------------ #
    # CR-1 / CR-2 · salidas
    # ------------------------------------------------------------------ #
    def _salidas(self):
        self._encabezado(f"CR-1/CR-2 · SALIDAS ({TABLA_SALIDAS})")
        total = self._escalar(f"SELECT COUNT(*) FROM `{TABLA_SALIDAS}`")
        self.stdout.write(f"  Filas totales: {total}")

        self.stdout.write("  Distribución de estados:")
        for estado, n in self._consulta(
            f"SELECT IFNULL(estado,'(NULL)'), COUNT(*) FROM `{TABLA_SALIDAS}` "
            "GROUP BY estado ORDER BY COUNT(*) DESC"
        ):
            self.stdout.write(f"      {str(estado):<16} {n:>9}")

        # CR-1: (vehículo, día) repetido con estado vivo.
        cr1 = self._consulta(
            "SELECT id_vehiculo, fecha_salida, COUNT(*) AS n, "
            "GROUP_CONCAT(estado) FROM `" + TABLA_SALIDAS + "` "
            "WHERE IFNULL(estado, '') <> 'ELIMINADO' "
            "GROUP BY id_vehiculo, fecha_salida HAVING n > 1 ORDER BY n DESC"
        )
        self._reportar_colision(
            "CR-1 (vehículo, día) con estado vivo != ELIMINADO", cr1,
            "el UNIQUE parcial NO puede crearse sin deduplicar",
        )

        # CR-2: (móvil, día) repetido con estado vivo, sin sentinelas.
        in_sentinelas = ", ".join(["%s"] * len(SENTINELAS_MOVIL))
        cr2 = self._consulta(
            "SELECT movil_sale, fecha_salida, COUNT(*) AS n, "
            "GROUP_CONCAT(estado) FROM `" + TABLA_SALIDAS + "` "
            "WHERE IFNULL(estado, '') <> 'ELIMINADO' "
            f"AND movil_sale IS NOT NULL AND TRIM(movil_sale) <> '' "
            f"AND LOWER(TRIM(movil_sale)) NOT IN ({in_sentinelas}) "
            "GROUP BY movil_sale, fecha_salida HAVING n > 1 ORDER BY n DESC",
            list(SENTINELAS_MOVIL),
        )
        self._reportar_colision(
            "CR-2 (móvil, día) con estado vivo != ELIMINADO (sin sentinelas)", cr2,
            "el UNIQUE parcial de móvil NO puede crearse sin deduplicar",
        )

        # Cuántas filas usan sentinelas (información, no es error).
        n_sent = self._escalar(
            "SELECT COUNT(*) FROM `" + TABLA_SALIDAS + "` "
            "WHERE movil_sale IS NOT NULL "
            f"AND LOWER(TRIM(movil_sale)) IN ({in_sentinelas})",
            list(SENTINELAS_MOVIL),
        )
        self.stdout.write(f"  Filas con móvil sentinela ('disponible'/'0'): {n_sent}")

    def _reportar_colision(self, titulo, filas, mensaje):
        if not filas:
            self.stdout.write(self.style.SUCCESS(f"  [OK] {titulo}: sin colisiones."))
            return
        self.hallazgos_duros += len(filas)
        self.stdout.write(self.style.ERROR(
            f"  [!!] {titulo}: {len(filas)} colisión(es) -> {mensaje}."
        ))
        for valores in filas[: self.top]:
            self.stdout.write(f"      {valores}")

    # ------------------------------------------------------------------ #
    # Integridad referencial (huérfanos del ETL)
    # ------------------------------------------------------------------ #
    def _integridad(self):
        self._encabezado("INTEGRIDAD REFERENCIAL (huérfanos que el ETL debe resolver)")
        huerfanos_veh = self._escalar(
            "SELECT COUNT(DISTINCT s.id_vehiculo) FROM `" + TABLA_SALIDAS + "` s "
            "LEFT JOIN `" + TABLA_VEHICULOS + "` v ON v.id = s.id_vehiculo "
            "WHERE s.id_vehiculo IS NOT NULL AND v.id IS NULL"
        )
        self.stdout.write(f"  Salidas con id_vehiculo inexistente: {huerfanos_veh}")

        huerfanos_tec = self._escalar(
            "SELECT COUNT(DISTINCT s.cedula_tecnico) FROM `" + TABLA_SALIDAS + "` s "
            "LEFT JOIN `" + TABLA_PERSONAL + "` p ON TRIM(p.cedula) = TRIM(s.cedula_tecnico) "
            "WHERE s.cedula_tecnico IS NOT NULL AND TRIM(s.cedula_tecnico) <> '' "
            "AND p.id IS NULL"
        )
        self.stdout.write(f"  Técnicos (cédula) sin fila en personal: {huerfanos_tec}")

        sin_fecha = self._escalar(
            f"SELECT COUNT(*) FROM `{TABLA_SALIDAS}` "
            "WHERE fecha_salida IS NULL OR fecha_salida = '0000-00-00'"
        )
        self.stdout.write(f"  Salidas sin fecha_salida válida: {sin_fecha}")

        rango = self._consulta(
            f"SELECT MIN(fecha_salida), MAX(fecha_salida) FROM `{TABLA_SALIDAS}` "
            "WHERE fecha_salida IS NOT NULL AND fecha_salida <> '0000-00-00'"
        )
        if rango and rango[0][0]:
            self.stdout.write(f"  Rango de fechas: {rango[0][0]} -> {rango[0][1]}")
