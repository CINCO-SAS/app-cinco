"""
FlotaService — ABM del catálogo de vehículos (Tab Base Transportadores).

Referencia: PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md §5.3.

Reglas de negocio:
- Unicidad de placa (CR-3: la BD legacy no la tenía; se impone aquí y en BD).
- Semáforo SOAT/CDA EN SERVIDOR (>60 verde, 31–60 naranja, ≤30 rojo) — §5.3.
- Documentos validados por tipo/tamaño; QR regenerado bajo demanda (D-A8).
- Exclusión de motos del catálogo (D-A13) — garantizada por choices.
- Datos bancarios: upsert por CSV (CR-13) — ver importar_datos_bancarios_csv.
"""
import csv
import io
import re
from datetime import date

import qrcode
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from ..models import (
    DatosBancariosVehiculo,
    DocumentoVehiculo,
    EstadoSalida,
    Salida,
    Vehiculo,
)
from .vigencia import estado_vigencia

# Límites de subida de documentos (§5.3).
TIPOS_ARCHIVO_PERMITIDOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB

# Import CSV bancarios (CR-13): orden de columnas del legacy verificado en
# base_transportadores.php 605–610.
COLUMNAS_CSV_BANCARIOS = (
    "placa",
    "cedula_titular",
    "nombre_titular",
    "tipo_cuenta",
    "banco",
    "numero_cuenta",
)
CAMPOS_BANCARIOS = COLUMNAS_CSV_BANCARIOS[1:]


class FlotaService:
    """Única capa de reglas de negocio de la flota vehicular."""

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    @staticmethod
    def listar(query_params):
        """
        Filtros opcionales: placa, marca, tipo_vehiculo, tipo_contrato,
        ciudad_operacion, conductor (pk), activo, search (libre).
        """
        queryset = Vehiculo.objects.select_related("conductor_habitual").all()

        for param in ("placa", "marca", "referencia", "color", "nombre_propietario"):
            value = query_params.get(param)
            if value:
                queryset = queryset.filter(**{f"{param}__icontains": value})

        for param in ("tipo_vehiculo", "tipo_contrato", "ciudad_operacion"):
            value = query_params.get(param)
            if value:
                queryset = queryset.filter(**{f"{param}__iexact": value.upper()})

        conductor = query_params.get("conductor")
        if conductor:
            queryset = queryset.filter(conductor_habitual_id=conductor)

        activo = query_params.get("activo")
        if activo is not None and activo != "":
            queryset = queryset.filter(activo=str(activo).lower() in ("1", "true", "si"))

        search = query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(placa__icontains=search)
                | Q(marca__icontains=search)
                | Q(referencia__icontains=search)
                | Q(nombre_propietario__icontains=search)
                | Q(numero_motor__icontains=search)
                | Q(numero_vin__icontains=search)
            )

        return queryset.order_by("placa")

    @staticmethod
    def obtener(vehiculo_id):
        try:
            return Vehiculo.objects.select_related("conductor_habitual").get(
                pk=vehiculo_id
            )
        except Vehiculo.DoesNotExist:
            raise ValueError(f"No existe un vehículo con id {vehiculo_id}.")

    @staticmethod
    def catalogo_operativo():
        """
        E1 (§6): reemplaza al controlador externo ``get_vehiculos_transp``
        (``gerencia_informes_vehiculos_controlador.php``) que el backoffice
        llamaba para poblar el DataTable y el calendario de salidas.

        Devuelve SOLO vehículos activos (los inactivos no operan), con los
        campos que el front consume: icono por ``tipo_vehiculo``, semáforo
        SOAT/CDA **calculado en servidor** (el legacy lo hacía en JS con
        aritmética de fechas frágil) y el conductor habitual.
        """
        return (
            Vehiculo.objects.select_related("conductor_habitual")
            .filter(activo=True)
            .order_by("placa")
        )

    @staticmethod
    def ficha_documental(vehiculo_id, hoy=None):
        """
        Ficha + semáforo SOAT/CDA en servidor (§5.3, B8).
        Hoy es paramétrico para poder testear sin congelar el reloj.
        """
        vehiculo = FlotaService.obtener(vehiculo_id)
        hoy = hoy or date.today()
        documentos = {
            doc.tipo: doc
            for doc in vehiculo.documentos.all()
        }
        return {
            "vehiculo": vehiculo,
            "semaforo": {
                "soat": FlotaService._semaforo(vehiculo.fecha_soat, documentos, hoy),
                "cda": FlotaService._semaforo(vehiculo.fecha_cda, documentos, hoy),
            },
            "documentos": documentos,
        }

    @staticmethod
    def _semaforo(fecha_campo, documentos, hoy):
        """Combina la fecha del campo plano con el documento subido."""
        doc = documentos.get("SOAT") if fecha_campo is None else None
        fecha = fecha_campo or (doc.fecha_vencimiento if doc else None)
        return estado_vigencia(fecha, hoy)

    @staticmethod
    def escanear(contenido, hoy=None):
        """
        S1: el kiosco POSTea el texto decodificado del QR (D-A8 codifica
        la placa) y el backend resuelve el vehículo + su salida del día —
        lo que la pantalla del kiosco muestra antes de reportar (S6).

        Devuelve {"vehiculo": Vehiculo, "salida": Salida | None}.
        """
        placa = str(contenido or "").strip().upper()
        if not placa:
            raise ValueError("El contenido del QR está vacío.")
        return FlotaService._vehiculo_y_salida_dia(placa, hoy)

    @staticmethod
    def vehiculo_por_placa(placa, hoy=None):
        """
        S4 (kiosco): consulta por placa + estado de la salida del día.

        Mismo camino de resolución que S1 (`escanear`), pero recibiendo la
        placa directamente en la ruta en vez de decodificarla de un QR.
        """
        placa = str(placa or "").strip().upper()
        if not placa:
            raise ValueError("Debe indicar la placa del vehículo.")
        return FlotaService._vehiculo_y_salida_dia(placa, hoy)

    @staticmethod
    def _vehiculo_y_salida_dia(placa, hoy=None):
        """Resuelve placa → vehículo + salida viva del día (comparte S1/S4)."""
        vehiculo = Vehiculo.objects.filter(placa=placa).first()
        if vehiculo is None:
            raise ValueError(f"Vehículo no encontrado con placa {placa}.")
        hoy = hoy or timezone.localdate()
        salida = (
            Salida.objects.filter(vehiculo=vehiculo, fecha_salida=hoy)
            .exclude(estado=EstadoSalida.ELIMINADO)
            .order_by("-id")
            .first()
        )
        return {"vehiculo": vehiculo, "salida": salida}

    # ------------------------------------------------------------------ #
    # Escritura
    # ------------------------------------------------------------------ #
    @staticmethod
    def crear(datos, actor):
        """Alta de vehículo: placa única + contrato/coherencia básica."""
        placa = FlotaService._validar_placa_unica(datos.get("placa"))
        registros = FlotaService._sanear(datos)
        registros["placa"] = placa
        registros["creado_por"] = actor

        try:
            with transaction.atomic():
                vehiculo = Vehiculo.objects.create(**registros)
                FlotaService.generar_qr(vehiculo.pk)
                # `generar_qr` persiste `codigo_qr` en su propia instancia:
                # sin refrescar, el alta (POST /vehiculos/) devolvería el
                # campo vacío y el front no recibiría la URL del QR.
                vehiculo.refresh_from_db(fields=["codigo_qr"])
                return vehiculo
        except IntegrityError:
            raise ValueError(
                "No se pudo crear el vehículo: la placa ya está registrada."
            )

    @staticmethod
    def actualizar(vehiculo_id, datos, actor, parche=False):
        vehiculo = FlotaService.obtener(vehiculo_id)

        merged = {} if parche else FlotaService._datos_base(vehiculo)
        merged.update(datos)

        if "placa" in merged:
            merged["placa"] = FlotaService._validar_placa_unica(
                merged["placa"], excluyendo=vehiculo_id
            )

        registros = FlotaService._sanear(merged)
        registros["modificado_por"] = actor

        placa_anterior = vehiculo.placa

        try:
            with transaction.atomic():
                for campo, valor in registros.items():
                    setattr(vehiculo, campo, valor)
                vehiculo.save()
                # El QR codifica la placa: si esta cambió hay que
                # regenerarlo y retirar el PNG huérfano, o `generar_qr`
                # devolvería el QR de la placa anterior (bug verificado).
                if vehiculo.placa != placa_anterior:
                    FlotaService.generar_qr(vehiculo.pk, forzar=True)
                    vehiculo.refresh_from_db(fields=["codigo_qr"])
        except IntegrityError:
            raise ValueError(
                "No se pudo actualizar el vehículo: la placa ya está registrada."
            )
        return vehiculo

    @staticmethod
    def inactivar(vehiculo_id, actor):
        """Baja lógica: activo=False. Nunca borrado físico (salidas → PROTECT)."""
        vehiculo = FlotaService.obtener(vehiculo_id)
        vehiculo.activo = False
        vehiculo.modificado_por = actor
        vehiculo.save(update_fields=["activo", "modificado_por", "modificado_en"])
        return vehiculo

    # ------------------------------------------------------------------ #
    # Documentos (§5.3)
    # ------------------------------------------------------------------ #
    @staticmethod
    def subir_documento(vehiculo_id, tipo, archivo, fecha_vencimiento, actor):
        """
        Adjunta o reemplaza un documento del vehículo (SOAT, CDA, MATRICULA,
        FOTO_CARRO, TARJETA_OPERACION). Unicidad (vehiculo, tipo): si ya
        existe, se actualiza el archivo (upsert, uq_doc_vehiculo_tipo).
        """
        vehiculo = FlotaService.obtener(vehiculo_id)

        if archivo is None:
            raise ValueError("El archivo es obligatorio.")
        if archivo.content_type not in TIPOS_ARCHIVO_PERMITIDOS:
            raise ValueError(
                "Tipo de archivo no permitido. Use JPG, PNG, WEBP o PDF."
            )
        if archivo.size > TAMANO_MAXIMO_BYTES:
            raise ValueError("El archivo excede el tamaño máximo de 5 MB.")

        documento, creado = DocumentoVehiculo.objects.get_or_create(
            vehiculo=vehiculo,
            tipo=tipo,
            defaults={
                "archivo": archivo,
                "fecha_vencimiento": fecha_vencimiento,
                "creado_por": actor,
            },
        )
        if not creado:
            documento.archivo = archivo
            documento.fecha_vencimiento = fecha_vencimiento
            documento.modificado_por = actor
            documento.save()
        return documento

    # ------------------------------------------------------------------ #
    # Import CSV bancarios (CR-13 / §5.3)
    # ------------------------------------------------------------------ #
    @staticmethod
    def limpiar_texto(valor):
        """
        Réplica de limpiarTexto() del legacy (base_transportadores.php 14–18):
        elimina todo carácter fuera de [a-zA-Z0-9\\s] y sube a mayúsculas.
        """
        return re.sub(r"[^a-zA-Z0-9\s]", "", valor or "").strip().upper()

    @staticmethod
    def detectar_separador(primera_linea):
        """Auto-detección delimitador: ';' si la cabecera lo tiene, si no ','."""
        return ";" if ";" in (primera_linea or "") else ","

    @staticmethod
    def importar_datos_bancarios_csv(archivo, actor=None):
        """
        Importación masiva de datos bancarios con lógica UPSERT por placa (CR-13):
        1) Auto-detección del separador (';' vs ',').
        2) Sanitización alfanumérica estricta de textos y cuentas.
        3) Si el vehículo ya tiene cuenta → actualiza; si no → la crea.
        4) Reporta filas rechazadas con causa explícita (mejora sobre el
           legacy, que solo devolvía 'Fila: N').

        Devuelve: {'insertados', 'actualizados', 'filas', 'errores'}.
        """
        if archivo is None:
            raise ValueError("El archivo CSV es obligatorio.")

        contenido = archivo.read()
        if isinstance(contenido, bytes):
            contenido = contenido.decode("utf-8", errors="replace")
        lineas = contenido.splitlines()
        if len(lineas) < 2:
            raise ValueError("El archivo CSV está vacío o solo tiene cabecera.")

        separador = FlotaService.detectar_separador(lineas[0])
        filas_procesadas = 0
        insertados = 0
        actualizados = 0
        errores = []

        lector = csv.reader(io.StringIO("\n".join(lineas[1:])), delimiter=separador)
        for indice, fila in enumerate(lector, start=2):  # 2 = cabecera incluida
            filas_procesadas += 1
            limpios = {
                columna: FlotaService.limpiar_texto(fila[i] if i < len(fila) else "")
                for i, columna in enumerate(COLUMNAS_CSV_BANCARIOS)
            }

            faltantes = [c for c in COLUMNAS_CSV_BANCARIOS if not limpios[c]]
            if faltantes:
                errores.append({
                    "fila": indice,
                    "causa": f"Campos vacíos: {', '.join(faltantes)}.",
                })
                continue

            try:
                vehiculo = Vehiculo.objects.get(
                    placa=limpios["placa"], activo=True
                )
            except Vehiculo.DoesNotExist:
                errores.append({
                    "fila": indice,
                    "causa": (
                        f"No existe vehículo ACTIVO con placa {limpios['placa']}."
                    ),
                })
                continue

            con_datos = {
                campo: limpios[campo] for campo in CAMPOS_BANCARIOS
            }
            with transaction.atomic():
                existente = DatosBancariosVehiculo.objects.filter(
                    vehiculo=vehiculo, activo=True
                ).first()
                if existente:
                    for campo, valor in con_datos.items():
                        setattr(existente, campo, valor)
                    existente.modificado_por = actor
                    existente.save()
                    actualizados += 1
                else:
                    DatosBancariosVehiculo.objects.create(
                        vehiculo=vehiculo,
                        creado_por=actor,
                        **con_datos,
                    )
                    insertados += 1

        return {
            "insertados": insertados,
            "actualizados": actualizados,
            "filas": filas_procesadas,
            "errores": errores,
        }

    # ------------------------------------------------------------------ #
    # QR de verificación (persistido en carpeta media y BD)
    # ------------------------------------------------------------------ #
    @staticmethod
    def generar_qr(vehiculo_id, forzar=False):
        """
        Genera el QR de la placa y lo PERSISTE en la carpeta
        `media/transporte/codigos-qr/qr_{placa}.png` y en `vehiculo.codigo_qr`.

        Si el archivo ya existe y no se fuerza regeneración, retorna el
        contenido existente desde storage para máxima eficiencia (soporte
        directo para Planillas de despacho y generación de PDFs).
        """
        vehiculo = FlotaService.obtener(vehiculo_id)
        rel_path = f"transporte/codigos-qr/qr_{vehiculo.placa}.png"
        ruta_anterior = (
            vehiculo.codigo_qr.name if vehiculo.codigo_qr else ""
        )

        # La caché solo vale si el archivo apunta a la placa ACTUAL:
        # `actualizar` permite cambiar la placa, y sin esta comprobación
        # se devolvería el QR de la placa anterior (bug de verificación).
        if (
            not forzar
            and bool(vehiculo.codigo_qr)
            and vehiculo.codigo_qr.name == rel_path
            and default_storage.exists(rel_path)
        ):
            with default_storage.open(rel_path, "rb") as f:
                return f.read()

        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(vehiculo.placa)
        qr.make(fit=True)
        buffer = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(
            buffer, format="PNG"
        )
        contenido = buffer.getvalue()

        if default_storage.exists(rel_path):
            default_storage.delete(rel_path)
        nombre_guardado = default_storage.save(rel_path, ContentFile(contenido))

        if not vehiculo.codigo_qr or vehiculo.codigo_qr.name != nombre_guardado:
            vehiculo.codigo_qr = nombre_guardado
            vehiculo.save(update_fields=["codigo_qr"])

        # Si la placa cambió, el PNG de la placa anterior queda huérfano:
        # se retira, pero SOLO si está dentro de la carpeta del QR (nunca
        # se borra una ruta arbitraria de media).
        if (
            ruta_anterior
            and ruta_anterior != nombre_guardado
            and ruta_anterior.startswith("transporte/codigos-qr/")
            and default_storage.exists(ruta_anterior)
        ):
            default_storage.delete(ruta_anterior)

        return contenido

    @staticmethod
    def obtener_ruta_qr(vehiculo_id):
        """
        Retorna la ruta o archivo QR garantizando que exista en disco.
        Facilita el consumo inmediato en Planillas y reportes impresos.
        """
        vehiculo = FlotaService.obtener(vehiculo_id)
        rel_path = f"transporte/codigos-qr/qr_{vehiculo.placa}.png"
        if not vehiculo.codigo_qr or not default_storage.exists(rel_path):
            FlotaService.generar_qr(vehiculo_id, forzar=True)
            vehiculo.refresh_from_db(fields=["codigo_qr"])
        return vehiculo.codigo_qr

    # ------------------------------------------------------------------ #
    # Validaciones internas
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validar_placa_unica(placa, excluyendo=None):
        if not placa or not str(placa).strip():
            raise ValueError("La placa es obligatoria.")
        placa = str(placa).strip().upper()
        queryset = Vehiculo.objects.filter(placa=placa)
        if excluyendo:
            queryset = queryset.exclude(pk=excluyendo)
        if queryset.exists():
            raise ValueError(f"Ya existe un vehículo con la placa {placa}.")
        return placa

    @staticmethod
    def _sanear(datos):
        """Copia solo campos del modelo, normaliza a mayúsculas (D-A6) y valida catálogos."""
        campos = {f.name for f in Vehiculo._meta.fields}
        registros = {k: v for k, v in datos.items() if k in campos and k != "id"}
        for campo in ("placa", "tipo_vehiculo", "tipo_contrato", "marca"):
            if registros.get(campo) and isinstance(registros[campo], str):
                registros[campo] = registros[campo].strip().upper()
        FlotaService._validar_choices(registros)
        return registros

    @staticmethod
    def _validar_choices(registros):
        """
        Las choices de Django NO se validan a nivel de BD; aquí se imponen
        (D-A13: el catálogo no admite motos; D-A6: valores canónicos).
        """
        for campo, valor in registros.items():
            if valor in (None, ""):
                continue
            opciones = getattr(Vehiculo._meta.get_field(campo), "choices", None)
            if not opciones:
                continue
            validos = {clave for clave, _ in opciones}
            if valor not in validos:
                raise ValueError(
                    f"'{valor}' no es un valor válido para {campo}."
                )

    @staticmethod
    def _datos_base(vehiculo):
        return {f.name: getattr(vehiculo, f.name) for f in Vehiculo._meta.fields}
