"""Exporte del preventivo de PLANTA ELÉCTRICA a Excel.

No existe una plantilla fuente para este formulario, así que se aplica el
mismo lenguaje visual del módulo (banners borgoña, celdas amarillas de datos,
bordes negros y 12 columnas A..L) con secciones dinámicas:

- información general del sitio (pares etiqueta/valor),
- datos del reporte (jefatura, zona, modalidad, plan de mejora),
- un bloque por cada planta registrada con sus 7 filas de parámetros,
- diagnóstico por sistema (checklist) como tabla,
- pruebas y servicio de filtración con sus observaciones,
- hallazgos del plan de mejora con sus fotos,
- anexos fotográficos y transportes si los hubiera.

Las secciones vacías no se pintan y la numeración no deja huecos.
"""
from __future__ import annotations

from openpyxl import Workbook

from apps.smu.models import SmuActividad, SmuDetallePreventivoPlanta

from . import base
from .base import (
    ALIGN_LEFT,
    BORDER_NEGRO,
    FILL_BURGUNDY,
    FILL_GRIS_MEDIO,
    FILL_WHITE,
    FONT_HEADER_WHITE,
    Numerador,
    bloque_fotos,
    bloque_texto,
    encabezados_grupos,
    estilizar_fila,
    fila_banner,
    fusionar,
    par_de_campos,
    pares_con_datos,
    sub_titulo,
    texto_o_vacio,
)

HOJA = "Preventivo Planta"

# Tabla de diagnóstico: 6 columnas de la ficha repartidas sobre A..L.
GRUPOS_DIAGNOSTICO = [
    (1, 2),    # SISTEMA
    (3, 5),    # COMPONENTE
    (6, 6),    # ESTADO
    (7, 8),    # CAUSA
    (9, 10),   # CÓMO DETECTAR
    (11, 12),  # CÓMO CORREGIR
]
ENCABEZADOS_DIAGNOSTICO = [
    "SISTEMA", "COMPONENTE", "ESTADO", "CAUSA", "CÓMO DETECTAR", "CÓMO CORREGIR",
]


# ── Datos de la actividad ────────────────────────────────────────────────────

def _detalle(actividad: SmuActividad) -> SmuDetallePreventivoPlanta | None:
    try:
        return actividad.detalle_preventivo_planta
    except SmuDetallePreventivoPlanta.DoesNotExist:
        return None


def _pares_informacion_general(actividad: SmuActividad):
    izquierda = [
        ("NOMBRE DE ESTACIÓN:", texto_o_vacio(actividad.nombre_estacion)),
        ("REGIONAL:", texto_o_vacio(actividad.regional)),
        ("DIRECCIÓN:", texto_o_vacio(actividad.direccion)),
        ("SITE OWNER:", texto_o_vacio(actividad.site_owner)),
        ("EMPRESA:", texto_o_vacio(actividad.empresa)),
    ]
    derecha = [
        ("RESPONSABLE:", base.responsable(actividad)),
        ("COORDINADOR ALIADO:", texto_o_vacio(actividad.coordinador_aliado)),
        ("No. OT:", texto_o_vacio(actividad.codigo_ot)),
        ("FECHA EJECUCIÓN:", base.formato_fecha(actividad.fecha_inicio, con_hora=True)),
        ("FECHA FIN ACTIVIDAD:", base.formato_fecha(actividad.fecha_fin, con_hora=True)),
    ]
    return list(zip(izquierda, derecha))


def _pares_reporte(detalle: SmuDetallePreventivoPlanta, actividad: SmuActividad):
    izquierda = [
        ("JEFATURA:", texto_o_vacio(detalle.jefatura)),
        ("MODALIDAD:", texto_o_vacio(detalle.modalidad)),
        ("ESTRUCTURA:", texto_o_vacio(detalle.estructura)),
        ("FECHA DE ELABORACIÓN DEL INFORME:",
         base.formato_fecha(detalle.fecha_elaboracion_informe)),
    ]
    derecha = [
        ("ZONA O/M:", texto_o_vacio(detalle.zona_om)),
        ("CANTIDAD DE PLANTAS:", base.numero(detalle.cantidad_plantas)),
        ("No. OT / TAS:", texto_o_vacio(detalle.orden_trabajo_tas)),
        ("ESTADO DEL REPORTE:", actividad.get_estado_display()),
    ]
    return list(zip(izquierda, derecha))


def _pares_planta(planta) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    """Las 7 filas de la ficha de una planta, como pares etiqueta/valor."""
    n = base.numero
    return [
        (("MARCA DEL EQUIPO:", texto_o_vacio(planta.equipo_marca)),
         ("MODELO DEL EQUIPO:", texto_o_vacio(planta.equipo_modelo))),
        (("SERIAL DEL EQUIPO:", texto_o_vacio(planta.equipo_serial)),
         ("VELOCIDAD DEL MOTOR:", texto_o_vacio(planta.equipo_velocidad_motor))),
        (("ADMISIÓN DE AIRE:", texto_o_vacio(planta.equipo_admision_aire)),
         ("RPM:", n(planta.equipo_rpm))),
        (("HORAS DE TRABAJO:", n(planta.equipo_horas_trabajo)),
         ("FRECUENCIA (HZ):", n(planta.equipo_frecuencia_hz))),
        (("CAPACIDAD (KVA):", n(planta.equipo_capacidad_kva)),
         ("CAPACIDAD (KW):", n(planta.equipo_capacidad_kw))),
        (("DERRATEO:", texto_o_vacio(planta.equipo_derrateo)),
         ("CAPACIDAD DE DERRATEO:", texto_o_vacio(planta.equipo_capacidad_derrateo))),
        (("MARCA DEL MOTOR:", texto_o_vacio(planta.motor_marca)),
         ("MODELO DEL MOTOR:", texto_o_vacio(planta.motor_modelo))),
        (("SERIAL DEL MOTOR:", texto_o_vacio(planta.motor_serial)),
         ("PRESIÓN DE ACEITE:", n(planta.motor_presion_aceite))),
        (("TEMPERATURA DE ACEITE:", n(planta.motor_temp_aceite)),
         ("TEMPERATURA DEL REFRIGERANTE:", n(planta.motor_temp_refrigerante))),
        (("MARCA DEL GENERADOR:", texto_o_vacio(planta.generador_marca)),
         ("MODELO DEL GENERADOR:", texto_o_vacio(planta.generador_modelo))),
        (("SERIAL DEL GENERADOR:", texto_o_vacio(planta.generador_serial)),
         ("TEMPERATURA DEL AMBIENTE:", n(planta.generador_temp_ambiente))),
        (("TIPO DE BATERÍA:", texto_o_vacio(planta.bateria_tipo)),
         ("ESTADO DE LAS BATERÍAS:", texto_o_vacio(planta.bateria_estado))),
        (("ESTADO DEL CARGADOR:", texto_o_vacio(planta.bateria_estado_cargador)),
         ("VOLTAJE DE BATERÍAS (V):", n(planta.bateria_voltaje))),
        (("CAPACIDAD DE BATERÍA:", texto_o_vacio(planta.bateria_capacidad)),
         ("CANTIDAD DE BATERÍAS:", n(planta.bateria_cantidad))),
        (("VAC L1-L2:", n(planta.param_vac_l1_l2)),
         ("VAC L1-L3:", n(planta.param_vac_l1_l3))),
        (("VAC L2-L3:", n(planta.param_vac_l2_l3)),
         ("AMP L1:", n(planta.param_amp_l1))),
        (("AMP L2:", n(planta.param_amp_l2)),
         ("AMP L3:", n(planta.param_amp_l3))),
        (("CAPACIDAD (AMP):", n(planta.dimensionamiento_capacidad_amp)),
         ("CARGA DE DEMANDA (AMP):", n(planta.dimensionamiento_carga_demanda))),
        (("% DE CARGA:", n(planta.dimensionamiento_porc_carga)), ("", "")),
    ]


def _banner_subtitulo(ws, fila: int, texto: str) -> int:
    """Rótulo gris + bloque de pares debajo (usado dentro de secciones)."""
    fusionar(ws, fila, 1, fila, 12, valor=texto, fill=FILL_GRIS_MEDIO,
             font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
    return fila + 1


def _observaciones(ws, fila: int, rotulo: str, texto: str) -> int:
    fusionar(ws, fila, 1, fila, 12, valor=rotulo, fill=FILL_GRIS_MEDIO,
             font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
    fila += 1
    return bloque_texto(ws, fila, texto, 1, 12)


# ── Generador ────────────────────────────────────────────────────────────────

def construir_libro(actividad: SmuActividad) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = HOJA
    base.aplicar_anchos(ws)

    detalle = _detalle(actividad)
    plantas = list(actividad.plantas.all())
    checklist = list(actividad.checklist_planta.all())
    hallazgos = list(actividad.hallazgos_planta.all())
    transportes = list(actividad.transportes.all())
    evidencias = list(actividad.evidencias.all())

    numeros = Numerador()
    fila = 1

    # ── Encabezado del documento ────────────────────────────────────────────
    base.fila_espaciadora(ws, fila); fila += 1
    fila_banner(ws, fila, "DIRECCIÓN DE O&M RED DE ACCESO",
                FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
    fila_banner(ws, fila, "PLAN DE MANTENIMIENTO PREVENTIVO INTEGRAL RED MOVIL",
                FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
    fila_banner(ws, fila, "MANTENIMIENTO PREVENTIVO PLANTA ELÉCTRICA",
                FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
    base.fila_espaciadora(ws, fila); fila += 1

    # ── 1. Información general ──────────────────────────────────────────────
    pares_general = pares_con_datos(_pares_informacion_general(actividad))
    if pares_general:
        fila_banner(ws, fila, numeros.titulo("INFORMACIÓN GENERAL"),
                    FILL_BURGUNDY, FONT_HEADER_WHITE)
        fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        for par in pares_general:
            par_de_campos(ws, fila, par[0], par[1])
            fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

    # ── 2. Datos generales del reporte ──────────────────────────────────────
    if detalle is not None:
        pares_reporte = _pares_reporte(detalle, actividad)
        plan_mejora = texto_o_vacio(detalle.plan_mejora_estado)
        hay_datos = bool(
            pares_con_datos(pares_reporte, primero_siempre=False)
            or plan_mejora.strip()
        )
        if hay_datos:
            fila_banner(ws, fila, numeros.titulo("DATOS GENERALES DEL REPORTE"),
                        FILL_BURGUNDY, FONT_HEADER_WHITE)
            fila += 1
            base.fila_espaciadora(ws, fila); fila += 1
            for par in pares_con_datos(pares_reporte, primero_siempre=False):
                par_de_campos(ws, fila, par[0], par[1])
                fila += 1
            if plan_mejora.strip():
                fila = _observaciones(ws, fila, "PLAN DE MEJORA", plan_mejora)
            base.fila_espaciadora(ws, fila); fila += 1

    # ── 3. Plantas registradas (un bloque por planta) ───────────────────────
    if plantas:
        fila_banner(ws, fila, numeros.titulo("PLANTAS ELÉCTRICAS REGISTRADAS"),
                    FILL_BURGUNDY, FONT_HEADER_WHITE)
        fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        for indice, planta in enumerate(plantas, start=1):
            nombre = texto_o_vacio(planta.nombre_unidad)
            rotulo = f"PLANTA {indice}: {nombre}" if nombre else f"PLANTA {indice}"
            fila = _banner_subtitulo(ws, fila, rotulo)
            for par in pares_con_datos(_pares_planta(planta)):
                par_de_campos(ws, fila, par[0], par[1])
                fila += 1
            base.fila_espaciadora(ws, fila); fila += 1

    # ── 4. Diagnóstico por sistema ──────────────────────────────────────────
    if checklist:
        fila_banner(ws, fila,
                    numeros.titulo("DIAGNÓSTICO POR SISTEMA (LISTA DE CHEQUEO)"),
                    FILL_BURGUNDY, FONT_HEADER_WHITE)
        fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

        fila = encabezados_grupos(ws, fila, GRUPOS_DIAGNOSTICO,
                                  ENCABEZADOS_DIAGNOSTICO)
        for item in checklist:
            valores = [
                texto_o_vacio(item.sistema),
                texto_o_vacio(item.componente),
                texto_o_vacio(item.estado),
                texto_o_vacio(item.causa),
                texto_o_vacio(item.detectar),
                texto_o_vacio(item.corregir),
            ]
            fila = base.datos_grupos(ws, fila, GRUPOS_DIAGNOSTICO, valores,
                                     fill=FILL_WHITE, align=ALIGN_LEFT)
        base.fila_espaciadora(ws, fila); fila += 1

    # ── 5. Resultado de pruebas ─────────────────────────────────────────────
    if detalle is not None:
        pares_pruebas = [
            (("PRUEBA SIN CARGA (VACÍO):", texto_o_vacio(detalle.prueba_vacio)),
             ("PRUEBA CON CARGA:", texto_o_vacio(detalle.prueba_con_carga))),
            (("TRANSFERENCIA AUTOMÁTICA:",
              texto_o_vacio(detalle.prueba_transferencia_automatica)),
             ("PLANTA FORZADA:", texto_o_vacio(detalle.prueba_planta_forzada))),
        ]
        visibles = pares_con_datos(pares_pruebas, primero_siempre=False)
        observaciones = texto_o_vacio(detalle.observaciones_pruebas)
        if visibles or observaciones.strip():
            fila_banner(ws, fila, numeros.titulo("RESULTADO DE PRUEBAS"),
                        FILL_BURGUNDY, FONT_HEADER_WHITE)
            fila += 1
            base.fila_espaciadora(ws, fila); fila += 1
            for par in visibles:
                par_de_campos(ws, fila, par[0], par[1])
                fila += 1
            if observaciones.strip():
                fila = _observaciones(ws, fila, "OBSERVACIONES DE LAS PRUEBAS",
                                      observaciones)
            base.fila_espaciadora(ws, fila); fila += 1

    # ── 6. Servicio de filtración ───────────────────────────────────────────
    if detalle is not None:
        pares_filtracion = [
            (("CAMBIO DE ACEITE:", texto_o_vacio(detalle.cambio_aceite)),
             ("CAMBIO DE FILTROS DE AIRE:",
              texto_o_vacio(detalle.cambio_filtros_aire))),
            (("CAMBIO DE FILTROS DE COMBUSTIBLE:",
              texto_o_vacio(detalle.cambio_filtros_combustible)),
             ("CAMBIO DE FILTROS DE ACEITE:",
              texto_o_vacio(detalle.cambio_filtros_aceite))),
            (("CAMBIO DE MANGUERAS DEL PRECALENTADOR:",
              texto_o_vacio(detalle.cambio_mangueras_precalentador)),
             ("CAMBIO DE REFRIGERANTE:",
              texto_o_vacio(detalle.cambio_refrigerante))),
            (("CAMBIO DE BATERÍAS:", texto_o_vacio(detalle.cambio_baterias)),
             ("", "")),
        ]
        visibles = pares_con_datos(pares_filtracion, primero_siempre=False)
        observaciones = texto_o_vacio(detalle.observaciones_filtracion)
        if visibles or observaciones.strip():
            fila_banner(ws, fila, numeros.titulo("SERVICIO DE FILTRACIÓN"),
                        FILL_BURGUNDY, FONT_HEADER_WHITE)
            fila += 1
            base.fila_espaciadora(ws, fila); fila += 1
            for par in visibles:
                par_de_campos(ws, fila, par[0], par[1])
                fila += 1
            if observaciones.strip():
                fila = _observaciones(ws, fila, "OBSERVACIONES DE FILTRACIÓN",
                                      observaciones)
            base.fila_espaciadora(ws, fila); fila += 1

    # ── 7. Hallazgos (cada uno con sus fotos) ───────────────────────────────
    hallazgos_con_texto = [h for h in hallazgos
                           if texto_o_vacio(h.descripcion).strip()]
    if hallazgos_con_texto:
        fila_banner(ws, fila, numeros.titulo("HALLAZGOS — PLAN DE MEJORA"),
                    FILL_BURGUNDY, FONT_HEADER_WHITE)
        fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        for indice, hallazgo in enumerate(hallazgos, start=1):
            descripcion = texto_o_vacio(hallazgo.descripcion)
            if not descripcion.strip():
                continue
            fila = _banner_subtitulo(ws, fila, f"HALLAZGO {indice}")
            fila = bloque_texto(ws, fila, descripcion, 1, 12)
            fotos = [e for e in evidencias
                     if e.campo_origen.startswith(f"hallazgo_{indice}_")]
            if fotos:
                base.fila_espaciadora(ws, fila); fila += 1
                fila = bloque_fotos(ws, fila, fotos, titulo=base.rotulo_evidencia)
            else:
                base.fila_espaciadora(ws, fila); fila += 1

    # ── 8. Transportes (si la actividad los tuviera) ────────────────────────
    if transportes:
        fila_banner(ws, fila, numeros.titulo("TRANSPORTES"),
                    FILL_BURGUNDY, FONT_HEADER_WHITE)
        fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        for transporte in transportes:
            par_de_campos(
                ws, fila,
                ("TIPO DE TRANSPORTE:", texto_o_vacio(transporte.tipo_transporte)),
                ("CÓDIGO SAP:", texto_o_vacio(transporte.codigo_sap)),
            )
            fila += 1
            distancia = transporte.distancia_km
            detalle_transporte = texto_o_vacio(transporte.descripcion)
            if distancia not in (None, 0):
                kms = f"{float(distancia):g} km"
                detalle_transporte = (f"{detalle_transporte} ({kms})"
                                      if detalle_transporte else kms)
            if detalle_transporte:
                fila = _observaciones(ws, fila, "DESCRIPCIÓN", detalle_transporte)
            base.fila_espaciadora(ws, fila); fila += 1

    # ── 9. Anexos fotográficos (todo lo que no se usó arriba) ───────────────
    fotos_hallazgos = {
        e.id for e in evidencias
        if any(e.campo_origen.startswith(f"hallazgo_{i}_")
               for i in range(1, len(hallazgos) + 2))
    }
    anexos = [e for e in evidencias if e.id not in fotos_hallazgos]
    if anexos:
        fila_banner(ws, fila, numeros.titulo("ANEXOS FOTOGRÁFICOS"),
                    FILL_BURGUNDY, FONT_HEADER_WHITE)
        fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        fila = bloque_fotos(ws, fila, anexos, titulo=base.rotulo_evidencia)

    # ── Cierre: certificados, firmas y fotos de técnicos ─────────────────────
    # No son evidencias, así que ningún bloque anterior los coge: sin este
    # cierre se quedaban guardados en la base y fuera del reporte.
    fila = base.bloque_imagenes_adjuntas(
        ws, fila, actividad,
        titulo=lambda: numeros.titulo("CERTIFICADOS, TÉCNICOS Y FIRMAS"))

    estilizar_fila(ws, 1, border=BORDER_NEGRO)
    return wb


def generar_excel_preventivo_planta(actividad: SmuActividad) -> Workbook:
    """Devuelve el libro Excel del preventivo de planta eléctrica."""
    return construir_libro(actividad)
