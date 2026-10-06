import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from apps.smu.services.smu_maestras_loader import SmuMaestrasLoaderService


class Command(BaseCommand):
    help = 'Audita, deduplica y carga las tablas maestras de SMU (Estaciones y LPU) de forma segura.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--estaciones-json',
            type=str,
            help='Ruta al archivo JSON con los datos de las 979 estaciones'
        )
        parser.add_argument(
            '--lpu-json',
            type=str,
            help='Ruta al archivo JSON con los 1.718 registros LPU'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Ejecuta solo la validación, deduplicación y reporte sin escribir en la base de datos'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        estaciones_path = options.get('estaciones_json')
        lpu_path = options.get('lpu_json')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== {'[MODO AUDITORÍA DRY-RUN]' if dry_run else '[MODO ESCRITURA REAL]'} ==="
        ))

        if not estaciones_path and not lpu_path:
            self.stdout.write(self.style.WARNING(
                "No se especificó ninguna ruta de archivo. Use --estaciones-json o --lpu-json.\n"
                "Ejemplo: python manage.py poblar_maestras_smu --estaciones-json=data/estaciones.json --dry-run"
            ))
            return

        if estaciones_path:
            path = Path(estaciones_path)
            if not path.exists():
                raise CommandError(f"No se encontró el archivo: {estaciones_path}")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.stdout.write(f"\n--- Procesando Estaciones ({len(data)} registros) ---")
            res = SmuMaestrasLoaderService.procesar_estaciones(data, dry_run=dry_run)
            self.stdout.write(f"Total recibidos: {res['total_recibidos']}")
            self.stdout.write(self.style.SUCCESS(f"Total válidos 1FN: {res['total_validos']}"))
            self.stdout.write(self.style.WARNING(f"Duplicados omitidos: {res['total_duplicados_omitidos']}"))
            self.stdout.write(f"Inconsistencias: {res['total_inconsistencias']}")
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f"Insertados en BD: {res['insertados']} | Actualizados: {res['actualizados']}"))

        if lpu_path:
            path = Path(lpu_path)
            if not path.exists():
                raise CommandError(f"No se encontró el archivo: {lpu_path}")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.stdout.write(f"\n--- Procesando Catálogo LPU ({len(data)} registros) ---")
            res = SmuMaestrasLoaderService.procesar_matriz_lpu(data, dry_run=dry_run)
            self.stdout.write(f"Total recibidos: {res['total_recibidos']}")
            self.stdout.write(self.style.SUCCESS(f"Total válidos: {res['total_validos']}"))
            self.stdout.write(self.style.WARNING(f"Duplicados omitidos: {res['total_duplicados_omitidos']}"))
            self.stdout.write(f"Inconsistencias: {res['total_inconsistencias']}")
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(f"Insertados en BD: {res['insertados']} | Actualizados: {res['actualizados']}"))
