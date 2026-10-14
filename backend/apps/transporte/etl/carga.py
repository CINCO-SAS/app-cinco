"""
Carga de la ETL: FKs por cédula/placa (§7.3), lotes y conciliación (§7.2).

Cada `cargar_*` recibe las filas crudas del JSON, las convierte con
`convertidores` y escribe en lotes de `tamano_lote` (2.000 por defecto, §7.3).
La resolución de FKs es por código natural (cédula/placa), nunca por JOIN
hacia `Empleado` (que vive en otra BD — D-A10); se hacen consultas puntuales
y se cachean en memoria por corrida.

Todo lo que no se pueda convertir o cargar se acumula en un reporte en vez
de abortar: la ETL corre una vez por ambiente (cutover D1) y el DoD de C3
es "201.000 registros con conciliación = 0", con el reporte señalando lo
que la auditoría §7.1 debió prevenir.
"""
from django.db import IntegrityError, transaction

from apps.empleados.models import Empleado

from ..models import (
    Conductor,
    DatosBancariosVehiculo,
    FechaLimiteCierre,
    JefeValidador,
    Novedad,
    PagoVehiculoMensual,
    Salida,
    SalidaHistorial,
    Vehiculo,
)
from ..services import ParametrosService
from . import convertidores as conv
from . import normalizadores as nz


def en_lotes(filas, tamano_lote):
    """Divide `filas` en lotes de a `tamano_lote` (§7.3: 2.000/batch)."""
    lote = []
    for fila in filas:
        lote.append(fila)
        if len(lote) >= tamano_lote:
            yield lote
            lote = []
    if lote:
        yield lote


class _Cache:
    """Consulta puntual por código natural, memorizada por corrida."""

    def __init__(self):
        self._mapa = {}

    def obtener(self, clave, buscar):
        if clave not in self._mapa:
            self._mapa[clave] = buscar(clave)
        return self._mapa[clave]


def _nuevo_reporte(entidad, leidas):
    return {
        "entidad": entidad,
        "leidas": leidas,
        "convertidas": 0,
        "creadas": 0,
        "actualizadas": 0,
        "lotes": 0,
        "errores": [],
        "advertencias": [],
    }


def _error(reporte, indice, fila, exc):
    reporte["errores"].append({
        "fila": indice,
        "id_legacy": fila.get("id"),
        "motivo": str(exc),
    })


def _advertir(reporte, indice, mensaje):
    reporte["advertencias"].append({"fila": indice, "motivo": mensaje})


def cargar_conductores(filas, tamano_lote=2000, dry_run=False):
    """Upsert de `transporte_base_conductores` por cédula única."""
    reporte = _nuevo_reporte("conductores", len(filas))
    for lote in en_lotes(filas, tamano_lote):
        reporte["lotes"] += 1
        for indice, fila in enumerate(lote):
            try:
                datos = conv.convertir_conductor(fila)
            except ValueError as exc:
                _error(reporte, indice, fila, exc)
                continue
            reporte["convertidas"] += 1
            for advertencia in datos.get(conv.ADVERTENCIAS, []):
                _advertir(reporte, indice, advertencia)
            if dry_run:
                continue
            try:
                with transaction.atomic():
                    campos = {k: v for k, v in datos.items()
                              if not k.startswith("_")}
                    conductor, creada = Conductor.objects.get_or_create(
                        cedula=campos["cedula"], defaults=campos
                    )
                    if not creada:
                        for campo, valor in campos.items():
                            setattr(conductor, campo, valor)
                        conductor.save(update_fields=list(campos))
                        reporte["actualizadas"] += 1
                    else:
                        reporte["creadas"] += 1
            except (ValueError, IntegrityError) as exc:
                _error(reporte, indice, fila, exc)
    return reporte


def cargar_vehiculos(filas, tamano_lote=2000, dry_run=False):
    """Upsert de `transportadores_vehiculos` por placa + bancarios + pagos.

    Devuelve (reporte, mapa {id_vehiculo_legacy: pk}) para que las salidas
    (que referencian por ID legacy) resuelvan sin volver a tocar la fuente.
    """
    reporte = _nuevo_reporte("vehiculos", len(filas))
    mapa_legacy = {}
    cache_conductores = _Cache()

    def _conductor_id(cedula):
        return cache_conductores.obtener(
            cedula,
            lambda c: Conductor.objects.filter(cedula=c)
            .values_list("id", flat=True).first(),
        )

    for lote in en_lotes(filas, tamano_lote):
        reporte["lotes"] += 1
        for indice, fila in enumerate(lote):
            try:
                datos = conv.convertir_vehiculo(fila)
            except ValueError as exc:
                _error(reporte, indice, fila, exc)
                continue
            reporte["convertidas"] += 1
            for advertencia in datos.get(conv.ADVERTENCIAS, []):
                _advertir(reporte, indice, advertencia)
            if dry_run:
                continue
            try:
                with transaction.atomic():
                    campos = {k: v for k, v in datos.items()
                              if not k.startswith("_")}
                    placa = campos["placa"]
                    vehiculo, creada = Vehiculo.objects.get_or_create(
                        placa=placa, defaults=campos
                    )
                    if not creada:
                        for campo, valor in campos.items():
                            setattr(vehiculo, campo, valor)
                        vehiculo.save(update_fields=list(campos))
                        reporte["actualizadas"] += 1
                    else:
                        reporte["creadas"] += 1

                    cedula = datos.get(conv.CEDULA_CONDUCTOR)
                    if cedula:
                        cid = _conductor_id(cedula)
                        if cid:
                            vehiculo.conductor_habitual_id = cid
                            vehiculo.save(update_fields=["conductor_habitual"])
                        else:
                            _advertir(reporte, indice,
                                      "conductor cédula %s no existe" % cedula)
                    vehiculo.datos_bancarios.all().delete()
                    for fila_b in datos[conv.REL_BANCARIOS]:
                        DatosBancariosVehiculo.objects.create(
                            vehiculo=vehiculo, **fila_b
                        )
                    for fila_p in datos[conv.REL_PAGOS]:
                        PagoVehiculoMensual.objects.update_or_create(
                            vehiculo=vehiculo, mes=fila_p["mes"],
                            anio=fila_p["anio"], tipo=fila_p["tipo"],
                            defaults=fila_p,
                        )
                    if fila.get("id"):
                        mapa_legacy[fila["id"]] = vehiculo.pk
            except (ValueError, IntegrityError) as exc:
                _error(reporte, indice, fila, exc)
    return reporte, mapa_legacy


def cargar_salidas(filas, tamano_lote=2000, dry_run=False, mapa_vehiculos=None):
    """Insert de `transporte_registro_salida` + historial + novedad (§7.2).

    FKs resueltas por cód. natural: vehículo por ID legacy → respaldo placa;
    conductor y técnico por cédula (sin JOIN cross-DB, D-A10).
    """
    reporte = _nuevo_reporte("salidas", len(filas))
    mapa_vehiculos = mapa_vehiculos or {}
    cache_vehiculos = _Cache()
    cache_conductores = _Cache()
    cache_empleados = _Cache()

    def _vehiculo_pk(id_legacy, placa):
        if id_legacy in mapa_vehiculos:
            return mapa_vehiculos[id_legacy]
        return cache_vehiculos.obtener(
            placa,
            lambda p: Vehiculo.objects.filter(placa=p)
            .values_list("id", flat=True).first(),
        )

    def _conductor_id(cedula):
        return cache_conductores.obtener(
            cedula,
            lambda c: Conductor.objects.filter(cedula=c)
            .values_list("id", flat=True).first(),
        )

    def _empleado_id(cedula):
        return cache_empleados.obtener(
            cedula,
            lambda c: Empleado.objects.filter(cedula=c)
            .values_list("id", flat=True).first(),
        )

    for lote in en_lotes(filas, tamano_lote):
        reporte["lotes"] += 1
        for indice, fila in enumerate(lote):
            try:
                datos = conv.convertir_salida(fila)
            except ValueError as exc:
                _error(reporte, indice, fila, exc)
                continue
            reporte["convertidas"] += 1
            for advertencia in datos.get(conv.ADVERTENCIAS, []):
                _advertir(reporte, indice, advertencia)
            if dry_run:
                continue
            try:
                with transaction.atomic():
                    vpk = _vehiculo_pk(
                        datos.get("_id_vehiculo_legacy"), datos[conv.PLACA]
                    )
                    if not vpk:
                        raise ValueError(
                            "vehículo placa %s no existe" % datos[conv.PLACA]
                        )
                    valores = {k: v for k, v in datos.items()
                               if not k.startswith("_")}
                    salida = Salida.objects.create(
                        vehiculo_id=vpk, **valores
                    )
                    cedula = datos.get(conv.CEDULA_CONDUCTOR)
                    if cedula:
                        cid = _conductor_id(cedula)
                        if cid:
                            salida.conductor_id = cid
                            salida.save(update_fields=["conductor"])
                        else:
                            _advertir(
                                reporte, indice,
                                "conductor cédula %s no existe" % cedula,
                            )
                    tecnico = datos.get(conv.CEDULA_TECNICO)
                    if tecnico:
                        eid = _empleado_id(tecnico)
                        if eid:
                            salida.tecnico_asignado_id = eid
                            salida.save(update_fields=["tecnico_asignado"])
                        else:
                            _advertir(
                                reporte, indice,
                                "técnico cédula %s no existe" % tecnico,
                            )
                    for fila_h in datos[conv.REL_HISTORIAL]:
                        SalidaHistorial.objects.create(salida=salida, **fila_h)
                    if datos.get(conv.REL_NOVEDAD):
                        Novedad.objects.create(
                            salida=salida, **datos[conv.REL_NOVEDAD]
                        )
                    reporte["creadas"] += 1
            except (ValueError, IntegrityError) as exc:
                _error(reporte, indice, fila, exc)
    return reporte


def cargar_jefes(filas, tamano_lote=2000, dry_run=False):
    """`programacion_parametros` → JefeValidador (una fila JSON → N jefes)."""
    reporte = _nuevo_reporte("jefes", len(filas))
    cache_empleados = _Cache()

    def _empleado_id(cedula):
        return cache_empleados.obtener(
            cedula,
            lambda c: Empleado.objects.filter(cedula=c)
            .values_list("id", flat=True).first(),
        )

    for lote in en_lotes(filas, tamano_lote):
        reporte["lotes"] += 1
        for indice, fila in enumerate(lote):
            try:
                jefes = conv.convertir_jefes_fila(fila)
            except ValueError as exc:
                _error(reporte, indice, fila, exc)
                continue
            for jefe in jefes:
                reporte["convertidas"] += 1
                if dry_run:
                    continue
                eid = _empleado_id(jefe["empleado_cedula"])
                if not eid:
                    _error(reporte, indice, fila, ValueError(
                        "jefe cédula %s no existe" % jefe["empleado_cedula"]
                    ))
                    continue
                try:
                    with transaction.atomic():
                        ParametrosService.crear_jefe(
                            {
                                "empleado": eid,
                                "areas": jefe["areas"],
                                "carpetas_por_area": jefe["carpetas_por_area"],
                                "activo": jefe["activo"],
                            },
                            actor=None,
                        )
                        reporte["creadas"] += 1
                except (ValueError, IntegrityError) as exc:
                    _error(reporte, indice, fila, exc)
    return reporte


def cargar_cierres(filas, tamano_lote=2000, dry_run=False):
    """`..._fechas_limites` → FechaLimiteCierre, upsert (mes, anio) por año."""
    reporte = _nuevo_reporte("cierres", len(filas))
    for lote in en_lotes(filas, tamano_lote):
        reporte["lotes"] += 1
        for indice, fila in enumerate(lote):
            try:
                datos = conv.convertir_fecha_limite(fila)
            except ValueError as exc:
                _error(reporte, indice, fila, exc)
                continue
            reporte["convertidas"] += 1
            if dry_run:
                continue
            try:
                with transaction.atomic():
                    existente = FechaLimiteCierre.objects.filter(
                        mes=datos["mes"], anio=datos["anio"]
                    ).first()
                    if existente:
                        ParametrosService.actualizar_cierre(
                            existente.pk,
                            {"fecha_limite": datos["fecha_limite"]},
                            actor=None,
                        )
                        reporte["actualizadas"] += 1
                    else:
                        ParametrosService.crear_cierre(
                            {
                                "mes": datos["mes"],
                                "anio": datos["anio"],
                                "fecha_limite": datos["fecha_limite"],
                            },
                            actor=None,
                        )
                        reporte["creadas"] += 1
            except (ValueError, IntegrityError) as exc:
                _error(reporte, indice, fila, exc)
    return reporte


def conciliar(reportes, dry_run=False):
    """Conteos origen vs destino por entidad (§7.2). Discrepancia ≠ 0 → DoD
    de C3 falla; en dry-run no se compara (no se escribió nada)."""
    destino = {
        "conductores": Conductor,
        "vehiculos": Vehiculo,
        "salidas": Salida,
        "jefes": JefeValidador,
        "cierres": FechaLimiteCierre,
    }
    conciliacion = {}
    for reporte in reportes:
        entidad = reporte["entidad"]
        if dry_run:
            conciliacion[entidad] = None
            continue
        modelo = destino.get(entidad)
        if modelo is None:
            continue
        origen = reporte["convertidas"]
        total_bd = modelo.objects.count()
        conciliacion[entidad] = {
            "origen": origen,
            "destino": total_bd,
            "discrepancia": total_bd - origen,
        }
    return conciliacion
