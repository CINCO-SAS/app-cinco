# backend/apps/transporte/management/commands/backfill_duenos.py
"""
Backfill del módulo «Dueños de vehículos» (2026-10-26).

Recorre los vehículos existentes y, por cada cédula de propietario
distinta, crea su `DuenoVehiculo`, vincula el FK `vehiculo.dueno` y
copia las cuentas bancarias del vehículo al dueño (upsert por
(banco, numero_cuenta)). Así un dueño con N vehículos queda como
**una sola fila** con sus N vehículos.

Idempotente: dueños ya creados no se duplican, vehículos ya vinculados
no se reescriben y las cuentas existentes no se repiten.

Uso:
  manage.py backfill_duenos --dry-run   # solo reporta qué haría (sin escribir)
  manage.py backfill_duenos             # ejecuta
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.transporte.models import (
    DatosBancariosDueno,
    DatosBancariosVehiculo,
    DuenoVehiculo,
    Vehiculo,
)


class Command(BaseCommand):
    help = "Crea dueños desde los vehículos existentes (1 dueño → N vehículos)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No escribe nada; solo reporta lo que haría.",
        )

    def handle(self, *args, **kwargs):
        if kwargs["dry_run"]:
            self._dry_run()
        else:
            self._ejecutar()

    # ------------------------------------------------------------------ #
    def _dry_run(self):
        cedulas = set(
            (v.cedula_propietario or "").strip()
            for v in Vehiculo.objects.all()
            if (v.cedula_propietario or "").strip()
        )
        existentes = set(DuenoVehiculo.objects.values_list("cedula", flat=True))
        por_crear = sorted(cedulas - existentes)
        por_vincular = (
            Vehiculo.objects.filter(dueno__isnull=True)
            .exclude(cedula_propietario="")
            .exclude(cedula_propietario=None)
            .count()
        )
        cuentas = (
            DatosBancariosVehiculo.objects.filter(activo=True, vehiculo__dueno=None)
            .exclude(numero_cuenta="")
            .count()
        )
        self.stdout.write("=== DRY RUN (no se escribe nada) ===")
        self.stdout.write(f"  dueños distintos en vehículos : {len(cedulas)}")
        self.stdout.write(f"  dueños YA existentes         : {len(existentes)}")
        self.stdout.write(f"  dueños por crear             : {len(por_crear)}")
        for cedula in por_crear[:20]:
            self.stdout.write(f"    + {cedula}")
        if len(por_crear) > 20:
            self.stdout.write(f"    … y {len(por_crear) - 20} más")
        self.stdout.write(f"  vehículos por vincular       : {por_vincular}")
        self.stdout.write(f"  cuentas bancarias a copiar   : {cuentas}")

    # ------------------------------------------------------------------ #
    def _ejecutar(self):
        creados = 0
        vinculados = 0
        cuentas_copiadas = 0
        sin_cedula = 0

        with transaction.atomic():
            for vehiculo in Vehiculo.objects.all().select_related("dueno"):
                cedula = (vehiculo.cedula_propietario or "").strip()
                if not cedula:
                    sin_cedula += 1
                    continue

                dueno, creado = DuenoVehiculo.objects.get_or_create(
                    cedula=cedula,
                    defaults={
                        "nombre": (vehiculo.nombre_propietario or "").strip()
                        or cedula,
                        "celular": (vehiculo.celular_propietario or "").strip()
                        or None,
                    },
                )
                if creado:
                    creados += 1

                if vehiculo.dueno_id is None:
                    vehiculo.dueno = dueno
                    vehiculo.save(update_fields=["dueno", "modificado_en"])
                    vinculados += 1

                # Cuentas del vehículo → cuentas del dueño (upsert).
                for dato in DatosBancariosVehiculo.objects.filter(
                    vehiculo=vehiculo, activo=True
                ):
                    repetida = DatosBancariosDueno.objects.filter(
                        dueno=dueno,
                        banco=dato.banco,
                        numero_cuenta=dato.numero_cuenta,
                    ).exists()
                    if repetida:
                        continue
                    DatosBancariosDueno.objects.create(
                        dueno=dueno,
                        cedula_titular=dato.cedula_titular,
                        nombre_titular=dato.nombre_titular,
                        banco=dato.banco,
                        tipo_cuenta=dato.tipo_cuenta,
                        numero_cuenta=dato.numero_cuenta,
                        activo=True,
                    )
                    cuentas_copiadas += 1

        self.stdout.write("=== BACKFILL DE DUEÑOS ===")
        self.stdout.write(f"  dueños creados        : {creados}")
        self.stdout.write(f"  vehículos vinculados  : {vinculados}")
        self.stdout.write(f"  cuentas copiadas      : {cuentas_copiadas}")
        if sin_cedula:
            self.stdout.write(
                f"  vehículos sin cédula de propietario (ignorados): {sin_cedula}"
            )
