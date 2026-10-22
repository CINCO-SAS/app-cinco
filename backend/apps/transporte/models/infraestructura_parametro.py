"""
InfraestructuraParametro — proyección de SOLO LECTURA.

``infraestructura_parametros`` (BD **azul**, módulo de infraestructura) es una
tabla **polimórfica**: mezcla áreas y carpetas en filas con un campo ``tipo``.
Este modelo existe **únicamente** para resolver B11 — *área–carpeta con centro
de costos* (plan §6) — y para nada más.

Fuente legacy
------------
``controller_post.php:1127`` (acción ``json_area_carp``)::

    SELECT *, (SELECT id FROM infraestructura_parametros AS pra
               WHERE tipo = 'area' AND pra.valor = prc.condicion) AS id_area
    FROM infraestructura_parametros AS prc
    WHERE tipo = 'CARPETA' ORDER BY condicion ASC

De ahí sale ``map_carpetas`` en ``controller_cinco.js:3456``, que el backoffice
usa en dos sitios:

- ``base_salida_transporte.php:2146`` — pintar ``{ccosto} {área} - {carpeta}``.
- ``transporte_salida_informes.php:4189`` — agrupar la nómina por
  ``centro_costo + placa + mes`` (días, total, retefuente 1 %, total a pagar).

¿Por qué esta tabla y ninguna otra?
------------------------------------
Es la **única** del legacy que guarda ``centro_costo``. Se verificó que
``cinco_base_de_personal`` no tiene ni una columna de costo y que su JSON
``datos`` es de RRHH (hijos, vacunación, tallas, contactos de emergencia).

Lectura, nunca escritura
------------------------
- ``managed = False`` → Django **no emite ningún DDL** (ni ``CREATE`` ni
  ``ALTER`` ni ``DROP``) contra esta tabla. El esquema lo lleva el PHP.
- ``_database = "azul"`` → el ``MultiDBRouter`` la lee en la BD azul.
- ``save()``/``delete()``/``_insert``/``_update`` **lanzan**: aunque alguien
  escribiera ``.objects.create()`` por error, no llega a la BD. La promesa de
  solo lectura está **impuesta por el código**, no solo documentada.

Datos verificados sobre la BD real (2026-10-22): 90 filas ``tipo='CARPETA'``,
todas ``estado='ACTIVO'``; 6 carpetas ambiguas (mismo ``valor``, dos áreas y
dos centros de costo distintos) que se desambigúan con ``(carpeta, área)``.
"""
from django.db import models, NotSupportedError


class InfraestructuraParametro(models.Model):
    """``infraestructura_parametros`` — solo lectura (BD azul)."""

    _database = "azul"

    id = models.AutoField(primary_key=True)
    # 'AREA' (15 filas) o 'CARPETA' (90 filas) en la BD real.
    tipo = models.CharField(max_length=200)
    # En una fila tipo='CARPETA' guarda el NOMBRE de su área (FK por convención).
    condicion = models.CharField(max_length=200)
    # El nombre del área o de la carpeta.
    valor = models.CharField(max_length=255)
    # enum en MySQL: solo esas dos entradas.
    tipo_area = models.CharField(max_length=20, blank=True, null=True)
    # {"centro_costo": N, "subcentro_costo": N | [N]} — aquí vive B11.
    datos = models.JSONField(blank=True, null=True)
    parametros_agenda = models.JSONField(blank=True, null=True)
    edit = models.TextField(blank=True, null=True)
    fecha_edit = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "infraestructura_parametros"
        verbose_name = "Parámetro de infraestructura"
        verbose_name_plural = "Parámetros de infraestructura"
        # Nunca aparece en el admin: es ajeno a este módulo y es de solo
        # lectura; exponerlo invitaría a editarlo.
        default_permissions = ()

    def __str__(self):
        return "%s / %s = %s" % (self.tipo, self.condicion, self.valor)

    # ------------------------------------------------------------------ #
    # Guardas de solo lectura
    # ------------------------------------------------------------------ #
    # `managed=False` ya bloquea el DDL; esto bloquea el DML. Entre los dos,
    # la tabla no puede tocarla ni un error de dedo en el código. Los tests
    # insertan fixtures con `bulk_create` (que no llama a `save()`), que es
    # además la única vía de escritura que aquí se tolera.
    def save(self, *args, **kwargs):
        raise NotSupportedError(
            "infraestructura_parametros es de solo lectura: la gestiona el "
            "módulo legacy. Usa un SELECT (ParametrosService.centro_costos)."
        )

    def delete(self, *args, **kwargs):
        raise NotSupportedError(
            "infraestructura_parametros es de solo lectura: no se puede borrar."
        )
