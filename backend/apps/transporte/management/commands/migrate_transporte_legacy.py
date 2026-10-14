"""
ETL legacy → Django: manage.py migrate_transporte_legacy (F6 / §7 del plan).

Estructura armada en el Tramo A (A3) y validada de verdad recién en C3
cuando exista conectividad con la BD legacy (gate G2). Lee los JSON ya
exportados de `azul` (o de una muestra local con --fuente), los convierte
con `etl.convertidores` y escribe por lotes con `etl.carga`.

Nada se trunca: cada fila que no se pueda convertir o cargar queda en el
reporte (errores/advertencias) y la corrida sigue. El DoD de C3 exige
conciliación = 0 entre el conteo de origen y el de la BD destino; la
corrida termina con estado 1 si alguna discrepancia no es cero, para que
el cutover (D1) no avance sobre datos descuadrados.

Uso (dry-run, recomendado antes de escribir nada):

    manage.py migrate_transporte_legacy --dry-run
    manage.py migrate_transporte_legacy --fuente /ruta/export --lote 2000
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.transporte.etl import carga


class Command(BaseCommand):
    help = (
        "Migra el módulo transporte desde los JSON exportados del legacy "
        "hacia Django (lotes, conciliación y reporte de filas no "
        "convertibles). Corrida única por ambiente; validar en C3."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fuente",
            default="",
            help=(
                "Carpeta con los JSON exportados (por defecto: la muestra "
                "incluida en apps/transporte/etl/muestras)."
            ),
        )
        parser.add_argument(
            "--lote",
            type=int,
            default=2000,
            help="Filas por lote (§7.3: 2.000 por defecto).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Convierte y reporta sin escribir en la BD.",
        )

    def handle(self, *args, **opciones):
        fuente = Path(opciones["fuente"]) if opciones["fuente"] else _muestra()
        if not fuente.is_dir():
            raise CommandError(f"La carpeta fuente no existe: {fuente}")

        dry_run = opciones["dry_run"]
        lote = opciones["lote"]
        modo = "DRY-RUN (sin escritura)" if dry_run else "CARGA"
        self.stdout.write(f"ETL transporte → Django · modo {modo} · lote {lote}")

        reportes = []
        mapa_vehiculos = {}

        # Orden determinista por dependencias: conductores y vehículos antes
        # que salidas (FKs por cédula/placa, §7.3).
        entidades = [
            ("conductores", carga.cargar_conductores, False),
            ("vehiculos", carga.cargar_vehiculos, True),
            ("salidas", carga.cargar_salidas, False),
            ("jefes", carga.cargar_jefes, False),
            ("cierres", carga.cargar_cierres, False),
        ]

        for nombre, cargador, devuelve_mapa in entidades:
            filas = _leer(fuente, nombre, self.stdout)
            if filas is None:
                continue
            if nombre == "salidas":
                reporte = carga.cargar_salidas(
                    filas, lote, dry_run, mapa_vehiculos=mapa_vehiculos
                )
            elif devuelve_mapa:
                reporte, mapa_vehiculos = cargador(filas, lote, dry_run)
            else:
                reporte = cargador(filas, lote, dry_run)
            reportes.append(reporte)
            _resumen(reporte, self.stdout)

        conciliacion = carga.conciliar(reportes, dry_run=dry_run)
        descuadres = _conciliar(conciliacion, self.stdout)

        if not dry_run and descuadres:
            raise CommandError(
                f"Conciliación con {descuadres} discrepancia(s) ≠ 0: "
                "revisar el reporte antes de continuar con C3."
            )
        self.stdout.write(self.style.SUCCESS("ETL terminada."))


def _muestra():
    return Path(__file__).resolve().parents[2] / "etl" / "muestras"


def _leer(fuente, nombre, stdout):
    """Lee <fuente>/<nombre>.json; None si la entidad no está exportada."""
    ruta = fuente / f"{nombre}.json"
    if not ruta.exists():
        stdout.write(f"[{nombre}] ausente en la fuente → omitida")
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise CommandError(f"{ruta.name}: JSON inválido → {exc}")
    if not isinstance(datos, list):
        raise CommandError(f"{ruta.name}: se esperaba una lista de filas")
    return datos


def _resumen(reporte, stdout):
    # reporte["errores"/"advertencias"] son listas: se sacan del desempacado
    # y se pasan ya contadas, si no str.format() recibe la clave dos veces.
    conteos = {
        "errores": len(reporte["errores"]),
        "advertencias": len(reporte["advertencias"]),
    }
    stdout.write(
        "[{entidad}] leídas={leidas} convertidas={convertidas} "
        "creadas={creadas} actualizadas={actualizadas} lotes={lotes} "
        "errores={errores} advertencias={advertencias}".format(
            **{k: v for k, v in reporte.items() if k not in conteos},
            **conteos,
        )
    )
    for error in reporte["errores"]:
        stdout.write(
            f"    ✗ fila {error['fila']} (id={error['id_legacy']}): "
            f"{error['motivo']}"
        )
    for advertencia in reporte["advertencias"]:
        stdout.write(
            f"    ! fila {advertencia['fila']}: {advertencia['motivo']}"
        )


def _conciliar(conciliacion, stdout):
    """Imprime la tabla de conciliación y devuelve el nº de discrepancias."""
    descuadres = 0
    for entidad, fila in conciliacion.items():
        if fila is None:
            stdout.write(f"[{entidad}] conciliación: omitida (dry-run)")
            continue
        if fila["discrepancia"] == 0:
            stdout.write(
                f"[{entidad}] conciliación OK ({fila['origen']} = "
                f"{fila['destino']})"
            )
        else:
            descuadres += 1
            stdout.write(
                f"[{entidad}] DISCREPANCIA origen={fila['origen']} "
                f"destino={fila['destino']} Δ={fila['discrepancia']}"
            )
    return descuadres
