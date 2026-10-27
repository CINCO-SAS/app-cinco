"""
DuenoService — reglas de negocio del módulo «Dueños de vehículos».

Decisión del módulo (2026-10-26):
- El dueño es entidad propia: 1 dueño → N vehículos.
- Los datos bancarios viven en el DUEÑO (movidos de
  `DatosBancariosVehiculo`, que se conserva como compatibilidad).
- Asignar un vehículo NO lo roba de otro dueño: hay que quitarlo primero.
- Eliminar un dueño con vehículos asignados está bloqueado (los vehículos
  referencian al dueño con SET_NULL; la regla se resuelve aquí para no
  perder la relación sin querer).

Contrato ADMCINCO (D-A3): la vista solo enruta; todos los ValueError se
traducen a HTTP 400/404 en el ViewSet.
"""
from django.db import IntegrityError, transaction
from django.db.models import Count, Q

from ..models import DatosBancariosDueno, DuenoVehiculo, Vehiculo


class DuenoService:
    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar(query_params=None):
        """Tabla de dueños con `total_vehiculos` y `total_cuentas`.

        Búsqueda `?q=` sobre cédula o nombre y filtro `?activo=false`.
        """
        params = query_params or {}
        queryset = DuenoVehiculo.objects.annotate(
            total_vehiculos=Count("vehiculos", distinct=True),
            total_cuentas=Count(
                "datos_bancarios",
                filter=Q(datos_bancarios__activo=True),
                distinct=True,
            ),
        )
        busqueda = str(params.get("q") or "").strip()
        if busqueda:
            queryset = queryset.filter(
                Q(cedula__icontains=busqueda) | Q(nombre__icontains=busqueda)
            )
        if str(params.get("activo", "")).lower() in ("false", "0"):
            queryset = queryset.filter(activo=False)
        return queryset

    @staticmethod
    def obtener(dueno_id):
        from django.db.models import Prefetch
        try:
            return DuenoVehiculo.objects.prefetch_related(
                "vehiculos",
                Prefetch(
                    "datos_bancarios",
                    queryset=DatosBancariosDueno.objects.filter(activo=True),
                ),
            ).get(pk=dueno_id)
        except DuenoVehiculo.DoesNotExist:
            raise ValueError(f"No existe un dueño con id {dueno_id}.")

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @staticmethod
    def crear(datos, actor=None):
        """Alta de dueño; unicidad natural (cédula)."""
        cedula = str(datos.get("cedula") or "").strip()
        nombre = str(datos.get("nombre") or "").strip()
        celular = str(datos.get("celular") or "").strip()
        if not cedula:
            raise ValueError("La cédula del dueño es obligatoria.")
        if not nombre:
            raise ValueError("El nombre del dueño es obligatorio.")
        if not celular:
            raise ValueError("El teléfono o celular del dueño es obligatorio.")
        if DuenoVehiculo.objects.filter(cedula=cedula).exists():
            raise ValueError(f"Ya existe un dueño con la cédula {cedula}.")

        try:
            with transaction.atomic():
                return DuenoVehiculo.objects.create(
                    cedula=cedula,
                    nombre=nombre,
                    celular=celular,
                    activo=bool(datos.get("activo", True)),
                    creado_por=actor,
                )
        except IntegrityError:
            raise ValueError(f"Ya existe un dueño con la cédula {cedula}.")

    @staticmethod
    def actualizar(dueno_id, datos, actor=None):
        """Actualización con snapshot: los campos ausentes conservan su valor."""
        dueno = DuenoService.obtener(dueno_id)
        if "cedula" in datos:
            cedula = str(datos["cedula"] or "").strip()
            if not cedula:
                raise ValueError("La cédula del dueño es obligatoria.")
            if cedula != dueno.cedula and DuenoVehiculo.objects.filter(
                cedula=cedula
            ).exists():
                raise ValueError(f"Ya existe un dueño con la cédula {cedula}.")
            dueno.cedula = cedula
        if "nombre" in datos:
            nombre = str(datos["nombre"] or "").strip()
            if not nombre:
                raise ValueError("El nombre del dueño es obligatorio.")
            dueno.nombre = nombre
        if "celular" in datos:
            celular = str(datos["celular"] or "").strip()
            if not celular:
                raise ValueError("El teléfono o celular del dueño es obligatorio.")
            dueno.celular = celular
        if "activo" in datos:
            dueno.activo = bool(datos["activo"])

        try:
            with transaction.atomic():
                dueno.modificado_por = actor
                dueno.save()
        except IntegrityError:
            raise ValueError(f"Ya existe un dueño con la cédula {dueno.cedula}.")
        return dueno

    @staticmethod
    def eliminar(dueno_id):
        """Borrado físico bloqueado mientras el dueño tenga vehículos."""
        dueno = DuenoService.obtener(dueno_id)
        if dueno.vehiculos.exists():
            raise ValueError(
                "No se puede eliminar: el dueño tiene vehículos asignados. "
                "Quite primero los vehículos o inactivelo con `activo=false`."
            )
        dueno.delete()

    # ------------------------------------------------------------------ #
    # Vehículos del dueño (1 → N)
    # ------------------------------------------------------------------ #
    @staticmethod
    def asignar_vehiculo(dueno_id, datos, actor=None):
        """Asigna un vehículo EXISTENTE (por id o placa) al dueño.

        Un vehículo solo puede pertenecer a un dueño: si ya tiene otro,
        se rechaza con el nombre del dueño actual (hay que quitarlo antes).
        """
        dueno = DuenoService.obtener(dueno_id)
        vehiculo = DuenoService._vehiculo_desde(datos)

        if vehiculo.dueno_id == dueno.id:
            raise ValueError(
                f"El vehículo {vehiculo.placa} ya está asignado a este dueño."
            )
        if vehiculo.dueno_id is not None:
            actual = vehiculo.dueno
            raise ValueError(
                f"El vehículo {vehiculo.placa} ya pertenece al dueño "
                f"{actual.nombre} ({actual.cedula}); quítelo primero."
            )

        vehiculo.dueno = dueno
        vehiculo.modificado_por = actor
        vehiculo.save()
        return vehiculo

    @staticmethod
    def quitar_vehiculo(dueno_id, vehiculo_id, actor=None):
        """Desasigna el vehículo (queda sin dueño; no se borra el vehículo)."""
        dueno = DuenoService.obtener(dueno_id)
        vehiculo = DuenoService._vehiculo_desde({"vehiculo_id": vehiculo_id})
        if vehiculo.dueno_id != dueno.id:
            raise ValueError(
                f"El vehículo {vehiculo.placa} no está asignado a este dueño."
            )
        vehiculo.dueno = None
        vehiculo.modificado_por = actor
        vehiculo.save()
        return vehiculo

    # ------------------------------------------------------------------ #
    # Cuentas bancarias del dueño
    # ------------------------------------------------------------------ #
    @staticmethod
    def guardar_bancarios(dueno_id, cuentas, actor=None):
        """Reemplaza la lista de cuentas del dueño.

        - Cuentas con `id` existente → se actualizan.
        - Cuentas sin `id` → se crean.
        - Las ausentes de la lista → se dan de baja (`activo=False`),
          nunca se borran físicamente (trazabilidad de pagos ya girados).
        """
        dueno = DuenoService.obtener(dueno_id)
        existentes = {
            c.id: c
            for c in DatosBancariosDueno.objects.filter(dueno=dueno)
        }
        recibidas_ids = set()

        with transaction.atomic():
            for cuenta in cuentas:
                id_cuenta = cuenta.get("id")
                campos = {
                    "cedula_titular": str(cuenta.get("cedula_titular") or "").strip(),
                    "nombre_titular": str(cuenta.get("nombre_titular") or "").strip(),
                    "banco": str(cuenta.get("banco") or "").strip(),
                    "tipo_cuenta": str(cuenta.get("tipo_cuenta") or "").strip(),
                    "numero_cuenta": str(cuenta.get("numero_cuenta") or "").strip(),
                    "activo": bool(cuenta.get("activo", True)),
                }
                if id_cuenta:
                    fila = existentes.get(int(id_cuenta))
                    if fila is None:
                        raise ValueError(
                            f"La cuenta con id {id_cuenta} no pertenece "
                            "a este dueño."
                        )
                    for campo, valor in campos.items():
                        setattr(fila, campo, valor)
                    fila.modificado_por = actor
                    fila.save()
                    recibidas_ids.add(fila.id)
                    continue
                DatosBancariosDueno.objects.create(
                    dueno=dueno, creado_por=actor, **campos
                )

            # Baja lógica de las que no vinieron en la petición.
            for id_cuenta, fila in existentes.items():
                if id_cuenta not in recibidas_ids and fila.activo:
                    fila.activo = False
                    fila.modificado_por = actor
                    fila.save(update_fields=["activo", "modificado_por",
                                             "modificado_en"])

        # Se devuelven solo las cuentas activas: las dadas de baja se
        # conservan en la base (trazabilidad de pagos ya girados) pero no
        # se muestran ni pueden volver a activarse desde la ficha.
        return list(
            DatosBancariosDueno.objects.filter(
                dueno=dueno, activo=True
            ).order_by("id")
        )

    # ------------------------------------------------------------------ #
    # Auxiliares
    # ------------------------------------------------------------------ #
    @staticmethod
    def _vehiculo_desde(datos):
        """Resuelve el vehículo por `vehiculo_id` o por `placa`."""
        vehiculo_id = datos.get("vehiculo_id")
        placa = str(datos.get("placa") or "").strip().upper()
        try:
            if vehiculo_id:
                return Vehiculo.objects.select_related("dueno").get(pk=vehiculo_id)
            if placa:
                return Vehiculo.objects.select_related("dueno").get(placa=placa)
        except Vehiculo.DoesNotExist:
            clave = f"id {vehiculo_id}" if vehiculo_id else f"placa {placa}"
            raise ValueError(f"No existe un vehículo con {clave}.")
        raise ValueError("Indique `vehiculo_id` o `placa`.")
