"""
Dueño/propietario de vehículos — módulo nuevo «Dueños» (2026-10-26).

Antes los datos del dueño vivían embebidos en CADA fila de `Vehiculo`
(nombre/celular_propietario) y las cuentas bancarias eran de cada
vehículo: un dueño con N vehículos duplicaba sus datos N veces y al
cambiar un celular había que editarlo en todos. Aquí el dueño es
entidad propia — **1 dueño → N vehículos** — y sus cuentas bancarias
viven con él (movidas desde `DatosBancariosVehiculo`).

Compatibilidad (decisión del módulo): los campos `*_propietario` de
`Vehiculo` y el modelo `DatosBancariosVehiculo` **se mantienen intactos**
— el ETL, los informes y decenas de tests los siguen usando. El pagador
de los informes consulta primero la cuenta del DUEÑO y decae al
bancario del vehículo y luego al propietario.
"""
from django.db import models

from .base import AuditoriaModel


class DuenoVehiculo(AuditoriaModel):
    """Persona jurídica/natural dueña de uno o más vehículos de la flota."""

    cedula = models.CharField(max_length=20, unique=True, db_index=True)
    nombre = models.CharField(max_length=150)
    celular = models.CharField(max_length=30, null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "transporte_dueno_vehiculo"
        verbose_name = "Dueño de vehículo"
        verbose_name_plural = "Dueños de vehículos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.cedula} — {self.nombre}"


class DatosBancariosDueno(AuditoriaModel):
    """
    Cuentas bancarias del DUEÑO (CR-13 movido del vehículo al dueño).

    Un dueño puede tener varias cuentas; la vigente para pagar es la de
    menor id con `activo=True` (mismo criterio que el pagador del
    informe: orden `-id`, último creado gana).
    """

    dueno = models.ForeignKey(
        DuenoVehiculo, on_delete=models.CASCADE, related_name="datos_bancarios"
    )
    cedula_titular = models.CharField(max_length=20)
    nombre_titular = models.CharField(max_length=150)
    banco = models.CharField(max_length=80)
    tipo_cuenta = models.CharField(max_length=30)
    numero_cuenta = models.CharField(max_length=30)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "transporte_datos_bancarios_dueno"
        verbose_name = "Dato bancario de dueño"
        verbose_name_plural = "Datos bancarios de dueños"

    def __str__(self):
        return f"{self.nombre_titular} · {self.banco} {self.numero_cuenta}"
