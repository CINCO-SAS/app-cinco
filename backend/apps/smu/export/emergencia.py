"""Exporte del formulario de EMERGENCIAS (y correctivos estándar) a Excel.

Port dinámico de ``plantillaEmergencia.py``: mantiene el estilo (banners
borgoña, celdas amarillas, bordes negros, 12 columnas) pero **las secciones se
construyen según los datos que tenga la actividad**:

- una fila de información por dato no vacío (si no hay "No. TAS", no existe la fila),
- una fila de materiales por material registrado,
- la foto de cada material en su fila (FOTO ANTES / FOTO DESPUÉS), sin repetirla
  en el bloque general de evidencias,
- un bloque de fotos por cada dos evidencias,
- bloques de texto con altura propietional a lo largo del contenido,
- secciones sin datos simplemente no se pintan.

La maquetación es una guía (el usuario lo pidió "más o menos así"), así que
añade las filas que el formato original no traía y que sí son clave en la tabla
de gestión: N° de OT y EMPRESA.
"""
from __future__ import annotations

from openpyxl import Workbook

from apps.smu.models import (
    SmuActividad,
    SmuActividadTransporte,
    SmuDetalleFallaIntervencion,
)

from . import base
from .base import (
    ALIGN_LEFT,
    ALTO_FILA,
    ANCHO_MITAD,
    BORDER_NEGRO,
    BORDER_TABLA,
    FILL_BURGUNDY,
    FILL_GRIS_MEDIO,
    FILL_LIGHT_GRAY,
    FILL_WHITE,
    FILL_YELLOW,
    FONT_DATA_BOLD,
    FONT_DATA_REGULAR,
    FONT_HEADER_WHITE,
    bloque_texto as _bloque_texto,
    descripcion_material as _descripcion_material,
    estilizar_fila,
    fila_banner,
    filas_para_texto as _filas_para_texto,
    fusionar,
    par_de_campos as _par_de_campos,
    pares_con_datos as _pares_con_datos,
    responsable as _responsable,
    texto_o_vacio,
)
from .imagenes import insertar_foto_en_celda

HOJA = "Emergencia"


# ── Datos de la actividad ────────────────────────────────────────────────────

def _pares_informacion_general(actividad: SmuActividad):
    izquierda = [
        ("NOMBRE DE ESTACIÓN:", texto_o_vacio(actividad.nombre_estacion)),
        ("REGIONAL:", texto_o_vacio(actividad.regional)),
        ("DEPARTAMENTO:", texto_o_vacio(actividad.departamento)),
        ("DIRECCIÓN:", texto_o_vacio(actividad.direccion)),
        ("TIPO DE ESTACIÓN:", texto_o_vacio(actividad.tipo_estacion)),
        ("TIPO DE SITIO:", texto_o_vacio(actividad.tipo_sitio)),
        ("SITE OWNER:", texto_o_vacio(actividad.site_owner)),
        # Campos que la plantilla original no traía y que sí pide la tabla:
        ("No. OT:", texto_o_vacio(actividad.codigo_ot)),
    ]
    derecha = [
        ("CATEGORÍA:", actividad.get_categoria_display()),
        ("RESPONSABLE:", _responsable(actividad)),
        ("No. INC:", texto_o_vacio(actividad.numero_inc)),
        ("No. TAS:", texto_o_vacio(actividad.numero_tas)),
        ("FECHA EJECUCIÓN:", base.formato_fecha(actividad.fecha_inicio, con_hora=True)),
        ("FECHA FIN ACTIVIDAD:", base.formato_fecha(actividad.fecha_fin, con_hora=True)),
        ("¿IMPLICA EXCLUSIÓN?:", "SÍ" if actividad.implica_exclusion else "NO"),
        ("EMPRESA:", texto_o_vacio(actividad.empresa)),
    ]
    return list(zip(izquierda, derecha))


def _detalle(actividad: SmuActividad) -> SmuDetalleFallaIntervencion | None:
    try:
        return actividad.detalle_falla_intervencion
    except SmuDetalleFallaIntervencion.DoesNotExist:
        return None


def _pares_informacion_actividad(detalle: SmuDetalleFallaIntervencion | None):
    if detalle is None:
        return []
    return [
        (("TIPO DE ACTIVIDAD:", texto_o_vacio(detalle.tipo_actividad)),
         ("TIPO DE EQUIPO EN FALLA:", texto_o_vacio(detalle.tipo_equipo_falla))),
        (("MARCA:", texto_o_vacio(detalle.marca)),
         ("MODELO:", texto_o_vacio(detalle.modelo))),
        (("PRESENTA AFECTACIÓN DE SERVICIOS:", texto_o_vacio(detalle.afectacion_servicios)),
         ("REINSTALACIÓN:", texto_o_vacio(detalle.reinstalacion))),
        (("CAMBIO:", texto_o_vacio(detalle.cambio)),
         ("REPARACIÓN:", texto_o_vacio(detalle.reparacion))),
    ]


def _foto_material(evidencias, material, indice, parte):
    """Una de las dos fotos de la fila de un material (``antes``/``después``).

    Prioriza el vínculo ``material_id`` del modelo y, mientras siga sin
    llenarse (el frontend todavía no lo escribe), cae en el pareo posicional
    que sí construye: ``material_<n>_foto_<parte>``, donde ``n`` es la posición
    del material en la lista, la misma con la que se crearon.
    """
    vinculadas = [ev for ev in evidencias if ev.material_id == material.id]
    if vinculadas:
        posicion = 0 if parte == 'antes' else 1
        return vinculadas[posicion] if len(vinculadas) > posicion else None
    esperado = f'material_{indice}_foto_{parte}'
    for ev in evidencias:
        if ev.campo_origen == esperado:
            return ev
    return None


# ── Generador ────────────────────────────────────────────────────────────────

def construir_libro(actividad: SmuActividad) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = HOJA
    base.aplicar_anchos(ws)

    materiales = list(actividad.materiales.all())
    evidencias = list(actividad.evidencias.all())
    transportes = list(actividad.transportes.all())
    detalle = _detalle(actividad)
    # Fotos ya incrustadas en la fila de un material: no se repiten en el
    # bloque general de evidencias.
    fotos_usadas = set()

    fila = 1

    # ── Encabezado del documento ────────────────────────────────────────────
    base.fila_espaciadora(ws, fila); fila += 1
    fila_banner(ws, fila, "DIRECCIÓN DE O&M RED DE ACCESO", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
    fila_banner(ws, fila, "REPORTE DE MANTENIMIENTO DE EMERGENCIA", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
    fila_banner(ws, fila, "RED MÓVIL", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
    base.fila_espaciadora(ws, fila); fila += 1

    # ── 1. Información general ──────────────────────────────────────────────
    pares_general = _pares_con_datos(_pares_informacion_general(actividad))
    if pares_general:
        fila_banner(ws, fila, "1. INFORMACIÓN GENERAL", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        for par in pares_general:
            _par_de_campos(ws, fila, par[0], par[1])
            fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

    # ── 2. Información de la actividad ──────────────────────────────────────
    pares_actividad = _pares_con_datos(_pares_informacion_actividad(detalle))
    if pares_actividad:
        fila_banner(ws, fila, "2. INFORMACIÓN DE LA ACTIVIDAD", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        for par in pares_actividad:
            _par_de_campos(ws, fila, par[0], par[1])
            fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

    # ── 3. Descripción de la falla y solución ───────────────────────────────
    descripcion_falla = texto_o_vacio(detalle.descripcion_falla if detalle else "")
    descripcion_solucion = texto_o_vacio(detalle.descripcion_solucion if detalle else "")
    if descripcion_falla.strip() or descripcion_solucion.strip():
        fila_banner(ws, fila, "3. DESCRIPCIÓN DE LA FALLA Y SOLUCIÓN", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

        fusionar(ws, fila, 1, fila, 12, valor="DESCRIPCIÓN DE LA FALLA",
                 fill=FILL_GRIS_MEDIO, font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
        fila += 1
        fila = _bloque_texto(ws, fila, descripcion_falla, 1, 12)
        base.fila_espaciadora(ws, fila); fila += 1

        fusionar(ws, fila, 1, fila, 12, valor="DESCRIPCIÓN DE LA SOLUCIÓN",
                 fill=FILL_GRIS_MEDIO, font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
        fila += 1
        fila = _bloque_texto(ws, fila, descripcion_solucion, 1, 12)
        base.fila_espaciadora(ws, fila); fila += 1

    # ── 4. Listado de materiales (1 fila por material) ──────────────────────
    if materiales:
        fila_banner(ws, fila, "4. LISTADO DE MATERIALES (MATERIAL DE BODEGA)",
                    FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

        # No.(A) | Comprado(B:C) | Descripción(D:G) | Cantidad(H) | Unidad(I) | Foto antes(J:K) | Foto después(L)
        encabezados = [
            "No.", "¿COMPRADO\nPOR OPERARIO?", "DESCRIPCIÓN DEL MATERIAL",
            "CANTIDAD", "TIPO DE\nUNIDAD", "FOTO\nANTES", "FOTO\nDESPUÉS",
        ]
        grupos = [(1, 1), (2, 3), (4, 7), (8, 8), (9, 9), (10, 10), (11, 12)]
        for (ini, fin), texto in zip(grupos, encabezados):
            fusionar(ws, fila, ini, fila, fin, valor=texto, fill=FILL_GRIS_MEDIO,
                     font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
        fila += 1

        for indice, material in enumerate(materiales, start=1):
            anclas = []
            for (ini, fin) in grupos:
                ancla = fusionar(ws, fila, ini, fila, fin, fill=FILL_YELLOW,
                                 font=FONT_DATA_REGULAR, border=BORDER_TABLA)
                anclas.append(ancla)
            ws.cell(row=fila, column=1).value = indice
            ws.cell(row=fila, column=1).fill = FILL_WHITE

            ws.cell(row=fila, column=2).value = "SÍ" if material.comprado_operario else "NO"
            ws.cell(row=fila, column=4).value = _descripcion_material(material)
            ws.cell(row=fila, column=8).value = float(material.cantidad_real or 0) or None
            ws.cell(row=fila, column=9).value = texto_o_vacio(material.unidad_medida) or None

            for parte, ancla in (('antes', anclas[5]), ('despues', anclas[6])):
                foto = _foto_material(evidencias, material, indice, parte)
                if foto is None:
                    continue
                fotos_usadas.add(foto.pk)
                insertar_foto_en_celda(ws, foto.ruta_archivo, ancla)

            fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

    # ── 5. Evidencias fotográficas (un bloque por cada 2 fotos) ──────────────
    # Las fotos que ya quedaron en la fila de su material no se repiten aquí;
    # una foto de material que no empareje con ninguna fila sigue en este
    # registro (mismo criterio que el exporte de CAPEX).
    restantes = [ev for ev in evidencias if ev.pk not in fotos_usadas]
    if restantes:
        fila_banner(ws, fila, "5. EVIDENCIAS FOTOGRÁFICAS", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1
        # La cabecera de cada caja es la descripción que el usuario escribió
        # para la foto; si no escribió nada, el nombre del campo.
        fila = base.bloque_fotos(ws, fila, restantes, titulo=base.rotulo_evidencia)

    # ── 6. Observaciones y hallazgos ─────────────────────────────────────────
    observaciones = texto_o_vacio(actividad.observaciones)
    hallazgos = texto_o_vacio(actividad.hallazgos)
    recomendaciones = texto_o_vacio(actividad.recomendaciones)
    actividad_realizada = texto_o_vacio(
        detalle.descripcion_generales if detalle else ""
    ) or texto_o_vacio(detalle.descripcion_fallas_componentes if detalle else "")

    con_observaciones = any(
        t.strip() for t in (observaciones, hallazgos, recomendaciones, actividad_realizada)
    )
    if con_observaciones:
        fila_banner(ws, fila, "6. OBSERVACIONES Y HALLAZGOS", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

        if observaciones.strip():
            fusionar(ws, fila, 1, fila, 12, valor="OBSERVACIONES DE LA ACTIVIDAD",
                     fill=FILL_GRIS_MEDIO, font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
            fila += 1
            fila = _bloque_texto(ws, fila, observaciones, 1, 12)
            base.fila_espaciadora(ws, fila); fila += 1

        if actividad_realizada.strip() or hallazgos.strip():
            fusionar(ws, fila, 1, fila, 6, valor="ACTIVIDAD",
                     fill=FILL_GRIS_MEDIO, font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
            fusionar(ws, fila, 7, fila, 12, valor="HALLAZGOS / PLAN DE MEJORA",
                     fill=FILL_GRIS_MEDIO, font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
            fila += 1

            contenido_hallazgos = hallazgos.strip()
            if recomendaciones.strip():
                separador = "\n" if contenido_hallazgos else ""
                contenido_hallazgos += f"{separador}RECOMENDACIONES: {recomendaciones.strip()}"

            filas = max(
                _filas_para_texto(actividad_realizada, ANCHO_MITAD),
                _filas_para_texto(contenido_hallazgos, ANCHO_MITAD),
            )
            fusionar(ws, fila, 1, fila + filas - 1, 6, valor=actividad_realizada or None,
                     fill=FILL_LIGHT_GRAY, font=FONT_DATA_REGULAR,
                     border=BORDER_TABLA, align=ALIGN_LEFT)
            fusionar(ws, fila, 7, fila + filas - 1, 12, valor=contenido_hallazgos or None,
                     fill=FILL_LIGHT_GRAY, font=FONT_DATA_REGULAR,
                     border=BORDER_TABLA, align=ALIGN_LEFT)
            for r in range(fila, fila + filas):
                ws.row_dimensions[r].height = ALTO_FILA
            fila += filas
            base.fila_espaciadora(ws, fila); fila += 1

    # ── 7. Transportes (1 fila por transporte) ───────────────────────────────
    if transportes:
        fila_banner(ws, fila, "7. TRANSPORTES ESPECIALES", FILL_BURGUNDY, FONT_HEADER_WHITE); fila += 1
        base.fila_espaciadora(ws, fila); fila += 1

        for transporte in transportes:
            _par_de_campos(
                ws, fila,
                ("DISTANCIA EN KM:", _distancia(transporte)),
                ("TIEMPO DE DESPLAZAMIENTO:", texto_o_vacio(transporte.tiempo_traslado)),
            )
            fila += 1
            _par_de_campos(
                ws, fila,
                ("TIPO DE TRANSPORTE:", texto_o_vacio(transporte.tipo_transporte)),
                ("CÓDIGO SAP:", texto_o_vacio(transporte.codigo_sap)),
            )
            fila += 1

            observacion = texto_o_vacio(transporte.observacion)
            if observacion.strip():
                fusionar(ws, fila, 1, fila, 12, valor="OBSERVACIÓN DE TRANSPORTE",
                         fill=FILL_GRIS_MEDIO, font=FONT_HEADER_WHITE, border=BORDER_NEGRO)
                fila += 1
                fila = _bloque_texto(ws, fila, observacion, 1, 12)

            base.fila_espaciadora(ws, fila); fila += 1

    # ── Certificados, firmas y fotos de técnicos ─────────────────────────────
    # Imágenes que no son evidencias: sin este cierre se quedaban en la base
    # y fuera del reporte. El número sigue al último bloque pintado.
    ultima_seccion = 4
    if restantes:
        ultima_seccion = 5
    if con_observaciones:
        ultima_seccion = 6
    if transportes:
        ultima_seccion = 7
    fila = base.bloque_imagenes_adjuntas(
        ws, fila, actividad,
        titulo=f"{ultima_seccion + 1}. CERTIFICADOS, TÉCNICOS Y FIRMAS")

    estilizar_fila(ws, 1, border=BORDER_NEGRO)
    return wb


def _distancia(transporte: SmuActividadTransporte) -> str:
    distancia = transporte.distancia_km
    if distancia in (None, 0):
        return ""
    return f"{float(distancia):g}"


def generar_excel_emergencia(actividad: SmuActividad) -> Workbook:
    """Devuelve el libro Excel del formulario de emergencias de la actividad."""
    return construir_libro(actividad)
