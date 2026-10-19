"""
Convertidores de la ETL: fila JSON legacy → kwargs de modelo (puros, sin BD).

La resolución de FKs por cédula/placa vive en `carga.py` (§7.3); aquí solo
se transforman formatos. Cada fila inválida lanza ValueError con el motivo
y el comando la acumula en el reporte de filas no convertibles (§7.2).

El `datos`/`historial` JSON se desempaqueta aquí (§7.2): bancarios[] →
DatosBancariosVehiculo, pago_mensual[]/pronto_pago[] → PagoVehiculoMensual,
novedad → Novedad, historial → SalidaHistorial, y los campos planos
valor_dia / area_sale / carpeta_sale / sede_sale mapean al modelo Salida.
"""
from ..models.choices import (
    CategoriaLicencia,
    TipoContrato,
    TipoNovedad,
    TipoPago,
    TipoVehiculo,
    TipoVinculacion,
)
from . import normalizadores as nz

# Claves internas que NO son campos de modelo (llevan guion bajo).
REL_BANCARIOS = "_bancarios"
REL_PAGOS = "_pagos"
REL_HISTORIAL = "_historial"
REL_NOVEDAD = "_novedad"
ADVERTENCIAS = "_advertencias"
PLACA = "_placa"
CEDULA_CONDUCTOR = "_cedula_conductor"
CEDULA_TECNICO = "_cedula_tecnico"

# Campos que el modelo NO persiste (verificado: se descartan en el modelo
# legacy → Django; se reportan como descarte para conciliar con §7.1).
DESCARTADOS_CONDUCTOR = (
    "nombre_propietario", "celular_propietario", "tipo_vehiculo", "placa",
    "edad", "edit", "fecha_edit",
)
DESCARTADOS_VEHICULO = (
    "como_cond", "contrato", "ultima_revicion", "edit", "fecha_edit",
    "img_carro", "img_soat", "img_cda", "img_matricula", "nombre_conductor",
)


def convertir_conductor(fila):
    """`transporte_base_conductores` → kwargs de Conductor (+ advertencias).

    `tipo_vinculacion` vive AQUÍ (columna 6 de esta tabla, plan §3.B y
    `Conductor.tipo_vinculacion`); en `transportadores_vehiculos` no existe.
    """
    cedula = nz.texto(fila.get("cedula"), "cedula", requerido=True)
    advertencias = []

    licencia = nz.texto(fila.get("licencia"))
    licencia_cat = None
    if licencia:
        if licencia.upper() in CategoriaLicencia.values:
            licencia_cat = licencia.upper()
        else:
            advertencias.append(
                f"licencia '{licencia}' fuera de catálogo → NULL"
            )

    # Legacy en minúsculas ('externo'/'interno') → catálogo D-A6. El campo
    # es NOT NULL con default EXTERNO: valor raro no tira la fila.
    vinculacion = nz.texto(fila.get("tipo_vinculacion"))
    if vinculacion and vinculacion.upper() in TipoVinculacion.values:
        vinculacion = vinculacion.upper()
    elif vinculacion:
        advertencias.append(
            f"tipo_vinculacion '{vinculacion}' fuera de catálogo → EXTERNO"
        )
        vinculacion = TipoVinculacion.EXTERNO
    else:
        vinculacion = TipoVinculacion.EXTERNO

    datos = {
        "cedula": cedula,
        "nombre_completo": nz.texto(
            fila.get("nombre_conductor"), "nombre_conductor", requerido=True
        ),
        "celular": nz.texto(fila.get("celular_conductor"), "celular_conductor"),
        "direccion": nz.texto(fila.get("direccion")) or None,
        "barrio": nz.texto(fila.get("barrio")) or None,
        "licencia_categoria": licencia_cat,
        "licencia_vencimiento": nz.fecha_legacy(
            fila.get("fecha_vencimiento_licencia")
        ),
        "tipo_vinculacion": vinculacion,
        "fecha_ingreso": nz.fecha_legacy(
            fila.get("fecha_ingreso"), "fecha_ingreso"
        ),
        "fecha_nacimiento": nz.fecha_legacy(
            fila.get("fecha_nacimiento"), "fecha_nacimiento"
        ),
        "fecha_egreso": nz.fecha_legacy(fila.get("fecha_egreso")),
        "activo": nz.activo_por_estado(fila.get("estado")),
        ADVERTENCIAS: advertencias,
    }
    if datos["fecha_ingreso"] is None:
        raise ValueError("fecha_ingreso vacía")
    return datos


def convertir_vehiculo(fila):
    """`transportadores_vehiculos` → kwargs de Vehiculo + bancarios + pagos."""
    datos_json = nz.json_columna(fila.get("datos")) or {}
    if not isinstance(datos_json, dict):
        raise ValueError("datos no es un objeto JSON")
    bancarios, pagos, advertencias = _desempaquetar_pagos(datos_json)

    return {
        "placa": nz.texto(fila.get("placa"), "placa", requerido=True).upper(),
        "tipo_vehiculo": nz.normalizar_catalogo(
            fila.get("tipo"), TipoVehiculo.values, "tipo_vehiculo"
        ),
        "tipo_contrato": nz.normalizar_catalogo(
            fila.get("tipo_contrato"), TipoContrato.values, "tipo_contrato"
        ),
        "marca": nz.texto(fila.get("marca"), "marca", requerido=True),
        "modelo_anio": nz.entero(fila.get("modelo"), "modelo"),
        "color": nz.texto(fila.get("color")),
        "municipio_matricula": nz.texto(fila.get("municipio_matricula")),
        "numero_motor": nz.texto(fila.get("numero_motor")),
        "tipo_combustible": nz.texto(fila.get("tipo_combustible")),
        "kilometraje": nz.entero(fila.get("kilometraje"), "kilometraje", True),
        "cajon": nz.booleano_si_no(fila.get("cajon")),
        "logos": nz.booleano_si_no(fila.get("logos")),
        "sistema_activo": nz.texto(fila.get("sistema_activo")) or None,
        "sistema_pasivo": nz.texto(fila.get("sistema_pasivo")) or None,
        # `tipo_vinculacion` NO existe en transportadores_vehiculos (§1 del
        # diccionario): vive en Conductor, no aquí (plan §3.B).
        "nombre_propietario": nz.texto(
            fila.get("propietario"), "propietario", requerido=True
        ),
        "cedula_propietario": nz.texto(
            fila.get("cedula"), "cedula_propietario", requerido=True
        ),
        "fecha_ingreso": nz.fecha_legacy(fila.get("fecha_ingreso")),
        "fecha_egreso": nz.fecha_legacy(fila.get("fecha_egreso")),
        "fecha_soat": nz.fecha_legacy(fila.get("fecha_soat")),
        "fecha_cda": nz.fecha_legacy(fila.get("fecha_cda")),
        "valor_dia_base": nz.decimal(fila.get("valor_dia"), "valor_dia"),
        "activo": nz.activo_por_estado(fila.get("estado")),
        # FK por cédula resuelta en carga.py (§7.3).
        CEDULA_CONDUCTOR: nz.texto(fila.get("cedual_conductor")) or None,
        REL_BANCARIOS: bancarios,
        REL_PAGOS: pagos,
        ADVERTENCIAS: advertencias,
    }


def _desempaquetar_pagos(datos_json):
    """`datos.bancarios[]` y `datos.pago_mensual[]/pronto_pago[]` (§7.2)."""
    bancarios = []
    pagos = []
    advertencias = []
    for i, fila in enumerate(datos_json.get("bancarios") or []):
        bancarios.append({
            "cedula_titular": nz.texto(
                fila.get("cedula"), "bancarios[%d].cedula" % i
            ),
            "nombre_titular": nz.texto(
                fila.get("nombre"), "bancarios[%d].nombre" % i
            ),
            "banco": nz.texto(fila.get("banco"), "bancarios[%d].banco" % i),
            "tipo_cuenta": nz.texto(
                fila.get("tipo_cuenta"), "bancarios[%d].tipo_cuenta" % i
            ),
            "numero_cuenta": nz.texto(
                fila.get("numero_cuenta"), "bancarios[%d].numero_cuenta" % i
            ),
        })
    for tipo, clave in ((TipoPago.MENSUAL, "pago_mensual"),
                        (TipoPago.PRONTO_PAGO, "pronto_pago")):
        for i, fila in enumerate(datos_json.get(clave) or []):
            mes = nz.entero(fila.get("mes"), "%s[%d].mes" % (clave, i))
            anio = nz.entero(fila.get("yyyy"), "%s[%d].yyyy" % (clave, i))
            pagos.append({
                "mes": mes,
                "anio": anio,
                "tipo": tipo,
                # `mes_aplicado`/`anio_aplicado`/`retroactivo` NO son columnas
                # de PagoVehiculoMensual: son de la sábana calculada (§5.2).
            })
    return bancarios, pagos, advertencias


def convertir_salida(fila):
    """`transporte_registro_salida` → kwargs de Salida + historial + novedad."""
    datos_json = nz.json_columna(fila.get("datos")) or {}
    if not isinstance(datos_json, dict):
        raise ValueError("datos no es un objeto JSON")

    movil = nz.texto(fila.get("movil_sale"), "movil_sale")
    es_disponible = movil.lower() in ("disponible", "0", "")
    advertencias = []

    placa_datos = nz.texto(datos_json.get("placa")).upper()
    if not placa_datos:
        raise ValueError("datos.placa ausente (FK de vehículo)")

    return {
        "fecha_salida": nz.fecha_legacy(fila.get("fecha_salida"), "fecha_salida"),
        "estado": nz.normalizar_estado(fila.get("estado")),
        "valor_dia": nz.decimal(datos_json.get("valor_dia"), "datos.valor_dia"),
        "observacion": nz.texto(fila.get("observacion")),
        "area": nz.texto(datos_json.get("area_sale")) or None,
        "carpeta": nz.texto(datos_json.get("carpeta_sale")) or None,
        "sede": nz.texto(datos_json.get("sede_sale")) or None,
        "es_disponible": es_disponible,
        # id_vehiculo es el FK legacy por ID; datos.placa es el respaldo de
        # resolución por cód. natural (carga.py decide cuál usar).
        "_id_vehiculo_legacy": nz.entero(
            fila.get("id_vehiculo"), "id_vehiculo", opcional=True
        ),
        PLACA: placa_datos,
        # 'disponible' → sin conductor; cédula → resuelta en carga.py.
        CEDULA_CONDUCTOR: None if es_disponible else movil,
        CEDULA_TECNICO: nz.texto(fila.get("cedula_tecnico")) or None,
        REL_HISTORIAL: _convertir_historial(fila.get("historial"), advertencias),
        REL_NOVEDAD: _convertir_novedad(datos_json.get("novedad")),
        ADVERTENCIAS: advertencias,
    }


def _convertir_historial(valor, advertencias):
    """`historial` longtext (JSON) → filas de SalidaHistorial (§7.2)."""
    historial_json = nz.json_columna(valor)
    if not historial_json:
        return []
    if not isinstance(historial_json, list):
        advertencias.append("historial no es lista JSON → ignorado")
        return []
    filas = []
    for i, entrada in enumerate(historial_json):
        if not isinstance(entrada, dict):
            continue
        estado = nz.texto(entrada.get("estado"))
        if not estado:
            continue
        try:
            estado = nz.normalizar_estado(estado)
        except ValueError as exc:
            # Un estado huérfano del historial NO tira la salida: se omite
            # y se reporta (la auditoría §7.1 decide el catálogo real).
            advertencias.append("historial[%d]: %s → omitida" % (i, exc))
            continue
        filas.append({
            "estado": estado,
            "motivo": nz.texto(entrada.get("motivo")),
            "fecha_cambio": nz.datetime_legacy(
                entrada.get("fecha_edit"), "historial[%d].fecha_edit" % i
            ),
        })
    return filas


def _convertir_novedad(valor):
    """`datos.novedad` → kwargs de Novedad; sin novedad → None."""
    if not isinstance(valor, dict) or not valor:
        return None
    if nz.booleano_si_no(valor.get("existe")) is False:
        return None
    tipo = nz.texto(valor.get("tipo"), "novedad.tipo", requerido=True)
    if tipo.upper() not in TipoNovedad.values:
        # La novedad mueve dinero: no se inventa tipo, se rechaza la fila.
        raise ValueError("novedad.tipo '%s' fuera de catálogo" % valor.get("tipo"))
    return {
        "tipo": tipo.upper(),
        "valor": nz.decimal(valor.get("valor"), "novedad.valor"),
        "descripcion": nz.texto(valor.get("descripcion")),
    }


def convertir_jefe(fila):
    """`programacion_parametros.datos[]` → kwargs de JefeValidador."""
    cedula = nz.texto(fila.get("cedula_jefe"), "cedula_jefe", requerido=True)
    carpetas = fila.get("carpetas") or {}
    if not isinstance(carpetas, dict):
        raise ValueError("carpetas no es un objeto JSON")
    return {
        "empleado_cedula": cedula,
        "areas": list(fila.get("areas") or []),
        "carpetas_por_area": carpetas,
        "activo": nz.activo_por_estado(fila.get("estado")),
    }


def convertir_jefes_fila(fila):
    """Fila de `programacion_parametros` → lista de jefes (datos = JSON)."""
    datos_json = nz.json_columna(fila.get("datos"))
    if datos_json is None:
        raise ValueError("datos no es JSON válido")
    if not isinstance(datos_json, list):
        raise ValueError("datos no es una lista de jefes")
    return [convertir_jefe(jefe) for jefe in datos_json]


def convertir_fecha_limite(fila):
    """`transporte_registro_salida_fechas_limites` → kwargs de FechaLimiteCierre.

    Un cierre sin fecha utilizable ('0000-00-00'/'') es fila NO convertible:
    se reporta en vez de dejar la conciliación descuadrada (§7.1.4).
    """
    fecha = nz.fecha_legacy(fila.get("fecha_limite"), "fecha_limite")
    if fecha is None:
        raise ValueError("fecha_limite ausente o fecha cero (0000-00-00)")
    return {
        "mes": nz.entero(fila.get("mes"), "mes"),
        "anio": nz.entero(fila.get("anio"), "anio"),
        "fecha_limite": fecha,
    }
