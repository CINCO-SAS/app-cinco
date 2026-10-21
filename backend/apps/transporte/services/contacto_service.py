"""
ContactoService — ficha de contacto del conductor (A1 de base_transportadores.php).

Legacy: `base_transportadores.php` 61–113, acción `get_telefonos_conductores`.
El legacy cruzaba TRES bases para armar la ficha del conductor:

  · cincosas_cincosas.nokia_base_lineas  (BD negra) → línea corporativa
        SELECT group_concat(distinct numero) FROM nokia_base_lineas WHERE asignado = ?
  · transporte_base_conductores.celular_conductor (azul) → celular del conductor
  · cinco_base_de_personal.celular_personal / celular_alterno / telefono_fijo (azul)

Motivo de cruzar tres: el número por el que de verdad contesta el conductor no
siempre es el que él anotó en transporte; puede ser el de RRHH o la línea
corporativa que la empresa le tiene asignada en Nokia.

Reglas de esta implementación:

  · D-A10 (cross-database): NUNCA JOIN hacia `Empleado` (vive en 'azul',
    managed=False). Se resuelve en dos pasos: cédula → `Empleado` (1 query),
    igual que hace `ParametrosService._adjuntar_empleados`.
  · La línea corporativa (BD negra) DEGRADA sin romper: si el alias 'negra'
    no está configurado (gate G2) se devuelve lista vacía y
    `nokia_disponible=False`, de modo que el front pueda avisar "no
    disponible" en vez de recibir un error.
  · Mejora sobre el legacy: `group_concat` devolvía "300111,300222" como una
    sola cadena y el front la pintaba tal cual; aquí se devuelve una LISTA de
    números, que es lo que el modal necesita para mostrar uno por línea.

Este servicio es de SOLO LECTURA: no escribe en ninguna base.
"""
from django.conf import settings

from apps.empleados.models import Empleado

from ..models import Conductor, Vehiculo
from .flota_service import FlotaService

# Alias de la base negra (Nokia). No está en DATABASES: aparece con el gate
# G2 (conectividad a las 3 bases). Si no existe, la línea corporativa se
# informa como no disponible.
ALIAS_NOKIA = "negra"

# Tabla y columna de la BD negra (del SQL del legacy).
TABLA_NOKIA_LINEAS = "cincosas_cincosas.nokia_base_lineas"
COLUMNA_NOKIA_NUMERO = "numero"
COLUMNA_NOKIA_ASIGNADO = "asignado"


class ContactoService:
    """Ficha de contacto del conductor de un vehículo."""

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    @staticmethod
    def contacto_vehiculo(vehiculo_id):
        """
        Ficha de contacto del conductor de un vehículo.

        Devuelve un dict con los 5 campos del legacy + metadatos de origen
        (`nokia_disponible`, `tiene_contacto`) para que el front pueda
        distinguir "no hay número" de "esa fuente no está disponible".
        """
        vehiculo = FlotaService.obtener(vehiculo_id)
        conductor = getattr(vehiculo, "conductor_habitual", None)

        datos = ContactoService._ficha_vacia(vehiculo_placa=vehiculo.placa)
        if conductor is None:
            return datos

        return ContactoService._completar_fuentes(datos, conductor)

    @staticmethod
    def contacto_conductor(conductor_id):
        """
        Ficha de contacto de un conductor suelto (sin vehículo).

        Útil para la pantalla de Conductores, donde no hay un vehículo de
        referencia. Reutiliza exactamente las mismas fuentes.
        """
        try:
            conductor = Conductor.objects.get(pk=conductor_id)
        except Conductor.DoesNotExist:
            raise ValueError(f"No existe un conductor con id {conductor_id}.")

        datos = ContactoService._ficha_vacia()
        return ContactoService._completar_fuentes(datos, conductor)

    # ------------------------------------------------------------------ #
    # Internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ficha_vacia(vehiculo_placa=None):
        """Estructura de la ficha con TODAS las fuentes en vacío."""
        return {
            "vehiculo_placa": vehiculo_placa,
            "conductor_cedula": None,
            "conductor_nombre": None,
            "linea_corporativa": [],
            "celular_conductor_externo": None,
            "celular_personal": None,
            "celular_alterno": None,
            "telefono_fijo": None,
            "nokia_disponible": False,
            "tiene_contacto": False,
        }

    @staticmethod
    def _completar_fuentes(datos, conductor):
        """Rellena la ficha con las 3 fuentes del legacy para un conductor."""
        datos["conductor_cedula"] = conductor.cedula
        datos["conductor_nombre"] = conductor.nombre_completo
        # `celular_conductor` del legacy = celular que el conductor anotó en
        # transporte (modelo Conductor.celular).
        datos["celular_conductor_externo"] = conductor.celular or None

        # --- Fuentes 2 y 3: transporte_base_conductores y cinco_base_de_personal ---
        empleado = ContactoService._empleado_por_cedula(conductor.cedula)
        if empleado is not None:
            datos["celular_personal"] = empleado.celular_personal or None
            datos["celular_alterno"] = empleado.celular_alterno or None
            datos["telefono_fijo"] = empleado.telefono_fijo or None

        # --- Fuente 1: línea corporativa (BD negra, gate G2) ---
        lineas, disponible = ContactoService._lineas_nokia(conductor.cedula)
        datos["linea_corporativa"] = lineas
        datos["nokia_disponible"] = disponible

        datos["tiene_contacto"] = ContactoService._tiene_contacto(datos)
        return datos

    # ------------------------------------------------------------------ #
    # Fuentes
    # ------------------------------------------------------------------ #
    @staticmethod
    def _empleado_por_cedula(cedula):
        """
        Resuelve el personal por cédula en la BD azul.

        Cross-database (D-A10): una sola query a `Empleado` (que el router
        manda a 'azul') y NUNCA un JOIN desde el módulo transporte.
        """
        if not cedula:
            return None
        return (
            Empleado.objects.filter(cedula=cedula)
            .only(
                "id",
                "cedula",
                "celular_personal",
                "celular_alterno",
                "telefono_fijo",
            )
            .first()
        )

    @staticmethod
    def _lineas_nokia(cedula):
        """
        Línea corporativa desde la BD negra (Nokia).

        Devuelve `(lineas, disponible)`.

        HOY devuelve `([], False)`: el alias 'negra' no está en DATABASES
        (gate G2 — conectividad a las 3 bases). Cuando se añada el alias, la
        consulta queda implementada aquí y basta con añadir el alias a
        settings; el resto del flujo no cambia.

        La degradación es deliberada: es preferible mostrar 4 de 5 fuentes con
        un aviso "no disponible" a devolver un 500 y dejar al usuario sin
        ninguna ficha.
        """
        if not cedula:
            return [], False
        if ALIAS_NOKIA not in settings.DATABASES:
            return [], False

        from django.db import connections

        try:
            with connections[ALIAS_NOKIA].cursor() as cursor:
                cursor.execute(
                    f"SELECT DISTINCT `{COLUMNA_NOKIA_NUMERO}` "  # noqa: S608
                    f"FROM `{TABLA_NOKIA_LINEAS}` "
                    f"WHERE `{COLUMNA_NOKIA_ASIGNADO}` = %s",
                    [cedula],
                )
                filas = cursor.fetchall()
        except Exception:  # noqa: BLE001 - la BD negra es opcional (gate G2)
            # Si la base no responde, la ficha se entrega igual sin la línea
            # corporativa: es información, no un flujo crítico.
            return [], False

        numeros = []
        for (numero,) in filas:
            if numero is None:
                continue
            texto = str(numero).strip()
            if texto and texto not in numeros:
                numeros.append(texto)
        return numeros, True

    # ------------------------------------------------------------------ #
    # Utilidades
    # ------------------------------------------------------------------ #
    @staticmethod
    def _tiene_contacto(datos):
        """¿Hay al menos un número con el que se pueda localizar al conductor?"""
        if datos.get("linea_corporativa"):
            return True
        for campo in (
            "celular_conductor_externo",
            "celular_personal",
            "celular_alterno",
            "telefono_fijo",
        ):
            if datos.get(campo):
                return True
        return False
