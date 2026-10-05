import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import django


def setup_django() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_date(date_str: Any) -> Optional[datetime.date]:
    if not date_str:
        return None
    val = normalize_text(date_str)
    # Puede venir en formato YYYY-MM-DD o con hora
    val = val.split(" ")[0].strip()
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migra agendamientos desde 'agenda_trabajos_cinco' (BD 'azul') a 'operaciones_agenda' (BD 'default')."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la migración sin escribir en la base de datos.",
    )
    parser.add_argument(
        "--years",
        nargs="+",
        default=["2026", "2027"],
        help="Años a migrar (por defecto: 2026 2027). Use --all-years para migrar todo el histórico.",
    )
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="Migra todos los años disponibles en la base de datos origen.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Tamaño de lote para lectura de la BD origen.",
    )
    parser.add_argument(
        "--output",
        default=str(Path("tmp") / "agenda_migration_log.csv"),
        help="Ruta del CSV donde se exporta el detalle de la migración.",
    )
    return parser


def fetch_legacy_rows(batch_size: int, years: Optional[List[str]] = None):
    from django.db import connections

    where_clause = ""
    params = []
    if years:
        placeholders = ", ".join(["%s"] * len(years))
        where_clause = f"WHERE yyyy IN ({placeholders})"
        params = years

    query = (
        f"SELECT id, cedula, sede, yyyy, mes, carpeta, edit, fecha_edit, datos "
        f"FROM agenda_trabajos_cinco {where_clause} ORDER BY id ASC"
    )

    with connections["azul"].cursor() as cursor:
        cursor.execute(query, params)
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                yield row


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_django()

    from django.contrib.auth import get_user_model
    from django.db import transaction
    from apps.operaciones.models.actividad_model import (
        Actividad,
        ActividadOT,
        ActividadDetalle,
        ActividadUbicacion,
        ActividadResponsableSnapshot,
    )
    from apps.operaciones.models.agenda_model import Agenda

    User = get_user_model()

    years_filter = None if args.all_years else args.years
    print(f"=== INICIO DE MIGRACIÓN DE AGENDA ===")
    print(f"Modo Dry-Run: {args.dry_run}")
    print(f"Años seleccionados: {'TODOS' if not years_filter else ', '.join(years_filter)}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Cargar caches en memoria para optimizar búsquedas masivas
    print("Cargando usuarios y actividades existentes en memoria...")
    user_cache: Dict[str, User] = {u.username: u for u in User.objects.all()}
    actividades_id_cache: Dict[int, Actividad] = {a.id: a for a in Actividad.objects.all()}
    actividades_ot_cache: Dict[str, Actividad] = {}
    for a in Actividad.objects.exclude(ot=""):
        ot_norm = normalize_text(a.ot).upper()
        if ot_norm and ot_norm not in actividades_ot_cache:
            actividades_ot_cache[ot_norm] = a

    for aot in ActividadOT.objects.select_related("actividad").filter(is_active=True):
        ot_norm = normalize_text(aot.ot).upper()
        if ot_norm and ot_norm not in actividades_ot_cache:
            actividades_ot_cache[ot_norm] = aot.actividad

    # Cache de agendas existentes en operaciones_agenda para asegurar idempotencia estricta
    # Clave: (responsable_id, actividad_id, fecha_inicio, fecha_fin, sede)
    agendas_existentes: Set[Tuple[int, int, str, str, str]] = set()
    for ag in Agenda.objects.filter(is_deleted=False).values_list(
        "responsable_id", "actividad_id", "fecha_inicio", "fecha_fin", "sede"
    ):
        agendas_existentes.add((
            ag[0],
            ag[1],
            str(ag[2]),
            str(ag[3]),
            normalize_text(ag[4]).lower(),
        ))
    print(f"Agendas ya existentes en base de datos: {len(agendas_existentes)}")

    # 2. Paso de extracción y deduplicación de eventos
    # Clave de deduplicación: (cedula, legacy_act_id, ot_norm, f_ini, f_fin, sede)
    dedup_events: Dict[Tuple[str, Optional[int], str, str, str, str], Dict[str, Any]] = {}

    total_rows = 0
    total_day_items = 0

    print("Leyendo filas legacy y deduplicando eventos diarios...")
    for row in fetch_legacy_rows(args.batch_size, years_filter):
        total_rows += 1
        source_id, cedula_padre, sede_padre, yyyy, mes, carpeta_padre, edit, fecha_edit, datos_raw = row
        if not datos_raw:
            continue

        try:
            datos = json.loads(datos_raw) if isinstance(datos_raw, str) else datos_raw
        except Exception:
            continue

        if not isinstance(datos, dict):
            continue

        cedula_p = normalize_text(cedula_padre)
        sede_p = normalize_text(sede_padre).lower() or "medellin"

        for dia_str, items in datos.items():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                total_day_items += 1

                cedula = normalize_text(it.get("cedula") or cedula_p)
                ot_raw = normalize_text(it.get("actividad") or "")
                # En algunos registros antiguos, la OT viene dentro de it['datos']['ot']
                datos_sub = it.get("datos")
                if not ot_raw and isinstance(datos_sub, dict):
                    ot_raw = normalize_text(datos_sub.get("ot") or datos_sub.get("OT UMBRELLA") or "")

                ot_norm = ot_raw.upper()

                legacy_act_id = None
                raw_leg_id = it.get("legacy_actividad_id")
                if raw_leg_id:
                    try:
                        legacy_act_id = int(raw_leg_id)
                    except (ValueError, TypeError):
                        pass

                f_ini_date = parse_date(it.get("fecha_inicio") or dia_str)
                f_fin_date = parse_date(it.get("fecha_fin") or it.get("fecha_inicio") or dia_str)

                if not f_ini_date or not f_fin_date:
                    continue

                if f_fin_date < f_ini_date:
                    f_fin_date = f_ini_date

                f_ini_str = str(f_ini_date)
                f_fin_str = str(f_fin_date)
                sede = normalize_text(it.get("sede") or sede_p).lower() or "medellin"

                dedup_key = (cedula, legacy_act_id, ot_norm, f_ini_str, f_fin_str, sede)
                if dedup_key not in dedup_events:
                    dedup_events[dedup_key] = {
                        "cedula": cedula,
                        "legacy_act_id": legacy_act_id,
                        "ot_norm": ot_norm,
                        "f_ini": f_ini_date,
                        "f_fin": f_fin_date,
                        "sede": sede,
                        "raw_item": it,
                        "edit": normalize_text(it.get("edit") or edit),
                        "fecha_edit": it.get("fecha_edit") or fecha_edit,
                    }

    print(f"Filas mensuales leídas: {total_rows}")
    print(f"Total items en días procesados: {total_day_items}")
    print(f"Total eventos únicos deduplicados a migrar: {len(dedup_events)}")

    # 3. Procesar e insertar en operaciones_agenda
    created_agendas = 0
    created_actividades = 0
    skipped_existing = 0
    missing_user_errors = 0

    csv_file = output_path.open("w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "evento_id",
        "cedula",
        "ot",
        "actividad_id",
        "fecha_inicio",
        "fecha_fin",
        "sede",
        "estado_migracion",
        "motivo",
    ])

    try:
        for idx, (dedup_key, ev) in enumerate(dedup_events.items(), start=1):
            if idx % 200 == 0 or idx == len(dedup_events):
                print(
                    f"\rProcesando eventos: {idx}/{len(dedup_events)} | "
                    f"Agendas creadas: {created_agendas} | Saltadas: {skipped_existing} | "
                    f"Nuevas Actividades: {created_actividades}",
                    end="",
                    flush=True,
                )

            cedula = ev["cedula"]
            ot_norm = ev["ot_norm"]
            legacy_act_id = ev["legacy_act_id"]
            f_ini = ev["f_ini"]
            f_fin = ev["f_fin"]
            sede = ev["sede"]
            raw_it = ev["raw_item"]
            edit_user_str = ev["edit"]

            # Resolver usuario responsable
            user = user_cache.get(cedula)
            if not user:
                missing_user_errors += 1
                csv_writer.writerow([
                    idx, cedula, ot_norm, legacy_act_id or "", str(f_ini), str(f_fin), sede,
                    "ERROR", f"Usuario con cédula {cedula} no existe en auth_user"
                ])
                continue

            # Resolver o crear Actividad
            actividad: Optional[Actividad] = None
            if legacy_act_id and legacy_act_id in actividades_id_cache:
                actividad = actividades_id_cache[legacy_act_id]
            elif ot_norm and ot_norm in actividades_ot_cache:
                actividad = actividades_ot_cache[ot_norm]

            # Si no existe la actividad, crearla si no estamos en dry-run
            if not actividad:
                ot_final = ot_norm or f"LEGACY-AGENDA-{idx}"
                obs_dia = raw_it.get("observaciones_dia") or {}
                color_hex = (obs_dia.get("color") if isinstance(obs_dia, dict) else None) or "#66bb6a"
                nombre_act = normalize_text(raw_it.get("nombre_act") or raw_it.get("actividad") or "LABOR AGENDADA")
                desc_detalle = normalize_text(raw_it.get("detalle_descripcion") or raw_it.get("observacion") or "")
                dir_ubicacion = normalize_text(raw_it.get("ubicacion_direccion") or "")
                zona_ub = normalize_text(raw_it.get("ubicacion_zona") or "")
                nodo_ub = normalize_text(raw_it.get("ubicacion_nodo") or "")
                lat = normalize_text(raw_it.get("latitud") or "")
                lon = normalize_text(raw_it.get("longitud") or "")

                if not args.dry_run:
                    with transaction.atomic():
                        actividad = Actividad.objects.create(
                            ot=ot_final,
                            estado="pendiente",
                            responsable_id=user.id,
                            fecha_inicio=f_ini,
                            fecha_fin_estimado=f_fin,
                            created_by=user.id,
                        )
                        ActividadOT.objects.create(
                            actividad=actividad,
                            ot=ot_final,
                            fecha_inicio=f_ini,
                            fecha_fin=f_fin,
                            is_active=True,
                            created_by=user.id,
                        )
                        ActividadDetalle.objects.create(
                            actividad=actividad,
                            tipo_trabajo=nombre_act[:100],
                            descripcion=desc_detalle,
                        )
                        ActividadUbicacion.objects.create(
                            actividad=actividad,
                            direccion=dir_ubicacion[:255] if dir_ubicacion else "N/A",
                            zona=zona_ub[:100],
                            nodo=nodo_ub[:100],
                            coordenada_x=lon[:100],
                            coordenada_y=lat[:100],
                        )
                        ActividadResponsableSnapshot.objects.create(
                            actividad=actividad,
                            empleado_id=user.id,
                            nombre=user.get_full_name() or user.username,
                            area=normalize_text(raw_it.get("area") or "OPERACIONES"),
                            carpeta=normalize_text(raw_it.get("carpeta") or "RESIDENCIAL"),
                            cargo="TÉCNICO",
                            movil="",
                        )

                    actividades_id_cache[actividad.id] = actividad
                    actividades_ot_cache[ot_final] = actividad
                created_actividades += 1

            actividad_id = actividad.id if actividad else (legacy_act_id or -1)

            # Verificar si ya existe en operaciones_agenda
            check_key = (user.id, actividad_id, str(f_ini), str(f_fin), sede)
            if check_key in agendas_existentes:
                skipped_existing += 1
                csv_writer.writerow([
                    idx, cedula, ot_norm, actividad_id, str(f_ini), str(f_fin), sede,
                    "SKIPPED", "Ya existe en operaciones_agenda"
                ])
                continue

            # Extraer color y observación
            obs_dia = raw_it.get("observaciones_dia") or {}
            color_hex = (obs_dia.get("color") if isinstance(obs_dia, dict) else None) or "#66bb6a"
            observacion = normalize_text(
                raw_it.get("detalle_descripcion")
                or raw_it.get("nombre_act")
                or raw_it.get("observacion")
                or ""
            )

            # Resolver auditoría del creador
            created_by_user = user_cache.get(edit_user_str) if edit_user_str else None

            if not args.dry_run and actividad:
                Agenda.objects.create(
                    actividad=actividad,
                    responsable=user,
                    fecha_inicio=f_ini,
                    fecha_fin=f_fin,
                    sede=sede,
                    color_hex=color_hex[:7],
                    observacion=observacion,
                    created_by=created_by_user,
                    updated_by=created_by_user,
                )
                agendas_existentes.add(check_key)

            created_agendas += 1
            csv_writer.writerow([
                idx, cedula, ot_norm, actividad_id, str(f_ini), str(f_fin), sede,
                "CREATED" if not args.dry_run else "DRY_RUN", "OK"
            ])
    finally:
        csv_file.close()

    print()
    print("=== MIGRACIÓN FINALIZADA ===")
    print(f"Total Agendas a Crear/Creadas: {created_agendas}")
    print(f"Total Agendas Saltadas (Ya existentes): {skipped_existing}")
    print(f"Nuevas Actividades Creadas en 'default': {created_actividades}")
    print(f"Errores por Usuario no encontrado: {missing_user_errors}")
    print(f"Reporte detallado generado en: {output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
