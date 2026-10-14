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
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Q

from ..models import DocumentoVehiculo, Vehiculo
from .vigencia import estado_vigencia

# Límites de subida de documentos (§5.3).
TIPOS_ARCHIVO_PERMITIDOS = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB


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
                return Vehiculo.objects.create(**registros)
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

        try:
            with transaction.atomic():
                for campo, valor in registros.items():
                    setattr(vehiculo, campo, valor)
                vehiculo.save()
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
