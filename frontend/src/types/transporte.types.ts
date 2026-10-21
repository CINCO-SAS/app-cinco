// src/types/transporte.types.ts
//
// Contratos del módulo Transporte. Los nombres replican EXACTAMENTE lo que
// expone el backend Django (serializers de apps/transporte/serializers/*),
// de modo que el front no traduce nada: consume el JSON tal cual.

// ---------------------------------------------------------------------------
// Catálogos (models/choices.py) — duplicados aquí porque el front necesita las
// etiquetas sin un round-trip. Mantener en sincronía con el backend.
// ---------------------------------------------------------------------------

export const ESTADOS_SALIDA = [
  "REPORTADO",
  "APROBADO",
  "RECHAZADO",
  "ELIMINADO",
  "VALIDADO",
] as const;
export type EstadoSalida = (typeof ESTADOS_SALIDA)[number];

export const TIPOS_VEHICULO = [
  "CAMIONETA",
  "FURGON",
  "VANS_CARGA",
  "VANS_PASAJEROS",
] as const;
export type TipoVehiculo = (typeof TIPOS_VEHICULO)[number];

export const TIPOS_CONTRATO = ["PROPIO", "EXTERNO", "RENTING"] as const;
export type TipoContrato = (typeof TIPOS_CONTRATO)[number];

export const CIUDADES_OPERACION = [
  "MEDELLIN",
  "MONTERIA",
  "SINCELEJO",
] as const;
export type CiudadOperacion = (typeof CIUDADES_OPERACION)[number];

export const CATEGORIAS_LICENCIA = ["B1", "C1", "C2", "C3"] as const;
export type CategoriaLicencia = (typeof CATEGORIAS_LICENCIA)[number];

export const TIPOS_VINCULACION = ["EXTERNO", "INTERNO"] as const;
export type TipoVinculacion = (typeof TIPOS_VINCULACION)[number];

export const TIPOS_DOCUMENTO_VEHICULO = [
  "SOAT",
  "CDA",
  "MATRICULA",
  "FOTO_CARRO",
  "TARJETA_OPERACION",
] as const;
export type TipoDocumentoVehiculo = (typeof TIPOS_DOCUMENTO_VEHICULO)[number];

export const TIPOS_MANTENIMIENTO = [
  "CORRECTIVO",
  "PREVENTIVO",
  "NO_APLICA",
] as const;
export type TipoMantenimiento = (typeof TIPOS_MANTENIMIENTO)[number];

export const TIPOS_NOVEDAD = ["ADICIONAL", "DESCUENTO"] as const;
export type TipoNovedad = (typeof TIPOS_NOVEDAD)[number];

export const TIPOS_PAGO = ["MENSUAL", "PRONTO_PAGO"] as const;
export type TipoPago = (typeof TIPOS_PAGO)[number];

// ---------------------------------------------------------------------------
// Semáforo de vigencia (services/vigencia.py) — calculado EN SERVIDOR.
// Regla: >60 días VIGENTE · 31–60 POR_VENCER · ≤30 o vencida VENCIDA.
// ---------------------------------------------------------------------------

export const ESTADOS_VIGENCIA = [
  "VIGENTE",
  "POR_VENCER",
  "VENCIDA",
  "SIN_REGISTRO",
] as const;
export type EstadoVigencia = (typeof ESTADOS_VIGENCIA)[number];

// ---------------------------------------------------------------------------
// Conductores (models/vehiculo.py · Conductor)
// ---------------------------------------------------------------------------

export interface Conductor {
  id: number;
  cedula: string;
  nombre_completo: string;
  celular: string;
  direccion: string | null;
  barrio: string | null;
  licencia_categoria: CategoriaLicencia | null;
  licencia_vencimiento: string | null;
  tipo_vinculacion: TipoVinculacion;
  fecha_ingreso: string;
  fecha_egreso: string | null;
  fecha_nacimiento: string | null;
  activo: boolean;
  /** Derivados solo en detalle (`ConductorSerializer`): nunca se persisten. */
  edad?: number | null;
  /** Semáforo §5.3 calculado EN SERVIDOR (también en el listado). */
  estado_licencia?: EstadoVigencia;
}

/**
 * Fila del listado (`ConductorListSerializer`): compacto, sin dirección ni
 * fechas de ingreso/egreso (esas llegan en el detalle al editar).
 */
export type ConductorListado = Pick<
  Conductor,
  | "id"
  | "cedula"
  | "nombre_completo"
  | "celular"
  | "tipo_vinculacion"
  | "licencia_categoria"
  | "licencia_vencimiento"
  | "activo"
> & {
  /** Siempre presente en el listado (calculado en servidor). */
  estado_licencia: EstadoVigencia;
};

// Referencia ligera embebida en los vehículos.
export interface ConductorReferencia {
  id: number;
  cedula: string;
  nombre_completo: string;
}

// ---------------------------------------------------------------------------
// Vehículos (models/vehiculo.py · Vehiculo)
// ---------------------------------------------------------------------------

export interface Vehiculo {
  id: number;
  placa: string;
  tipo_vehiculo: TipoVehiculo;
  marca: string;
  referencia: string | null;
  modelo_anio: number;
  color: string | null;
  municipio_matricula: string | null;
  numero_vin: string | null;
  numero_motor: string | null;
  tipo_combustible: string | null;
  kilometraje: number | null;
  cajon: boolean;
  logos: boolean;
  sistema_activo: string | null;
  sistema_pasivo: string | null;
  siniestros_viales: number;
  tipo_contrato: TipoContrato;
  ciudad_operacion: CiudadOperacion | null;
  conductor_habitual: number | null;
  conductor_habitual_detalle: ConductorReferencia | null;
  nombre_propietario: string;
  cedula_propietario: string;
  celular_propietario: string | null;
  fecha_ingreso: string | null;
  fecha_egreso: string | null;
  fecha_soat: string | null;
  fecha_cda: string | null;
  valor_dia_base: string;
  codigo_qr: string | null;
  activo: boolean;
  estado_soat: EstadoVigencia;
  estado_cda: EstadoVigencia;
}

/** Fila de listado (VehiculoListSerializer) — sin los campos pesados. */
export type VehiculoListado = Pick<
  Vehiculo,
  | "id"
  | "placa"
  | "marca"
  | "referencia"
  | "modelo_anio"
  | "tipo_vehiculo"
  | "tipo_contrato"
  | "ciudad_operacion"
  | "fecha_soat"
  | "fecha_cda"
  | "estado_soat"
  | "estado_cda"
  | "valor_dia_base"
  | "codigo_qr"
  | "activo"
>;

/** Payload de alta/edición (lo que envía el formulario). */
export interface VehiculoPayload {
  placa: string;
  tipo_vehiculo: TipoVehiculo;
  marca: string;
  referencia?: string | null;
  modelo_anio: number;
  color?: string | null;
  municipio_matricula?: string | null;
  numero_vin?: string | null;
  numero_motor?: string | null;
  tipo_combustible?: string | null;
  kilometraje?: number | null;
  cajon?: boolean;
  logos?: boolean;
  sistema_activo?: string | null;
  sistema_pasivo?: string | null;
  siniestros_viales?: number;
  tipo_contrato: TipoContrato;
  ciudad_operacion?: CiudadOperacion | null;
  conductor_habitual?: number | null;
  nombre_propietario: string;
  cedula_propietario: string;
  celular_propietario?: string | null;
  fecha_ingreso?: string | null;
  fecha_egreso?: string | null;
  fecha_soat?: string | null;
  fecha_cda?: string | null;
  valor_dia_base?: string;
  activo?: boolean;
}

// ---------------------------------------------------------------------------
// Documentos y mantenimientos (relaciones 1:N de Vehiculo)
// ---------------------------------------------------------------------------

export interface DocumentoVehiculo {
  id: number;
  vehiculo: number;
  tipo: TipoDocumentoVehiculo;
  archivo: string;
  fecha_vencimiento: string | null;
}

export interface Mantenimiento {
  id: number;
  vehiculo: number;
  fecha: string;
  tipo: TipoMantenimiento;
  actividad_realizada: string;
  responsable: string;
  observacion: string;
  proximo_mantenimiento: string | null;
}

export interface DatosBancariosVehiculo {
  id: number;
  vehiculo: number;
  cedula_titular: string;
  nombre_titular: string;
  banco: string;
  tipo_cuenta: string;
  numero_cuenta: string;
  activo: boolean;
}

// ---------------------------------------------------------------------------
// Salidas (models/salida.py · Salida) — el corazón del módulo
// ---------------------------------------------------------------------------

/**
 * Persona detrás de una salida. El backend devuelve SIEMPRE la misma forma
 * para `conductor_detalle` (quien sale) y `tecnico_asignado_detalle`
 * (móvil de nómina), aunque vienen de modelos distintos.
 */
export interface DetallePersona {
  nombre: string;
  cedula: string;
}

export interface Salida {
  id: number;
  vehiculo: number;
  vehiculo_placa: string;
  fecha_salida: string;
  conductor: number | null;
  /** Quién SALE (legacy `movil_sale`) — `null` si la salida es 'disponible'. */
  conductor_detalle: DetallePersona | null;
  tecnico_asignado: number | null;
  /** Móvil asignada de nómina (legacy `cc_asignada`), resuelta en servidor. */
  tecnico_asignado_detalle: DetallePersona | null;
  es_disponible: boolean;
  area: string | null;
  carpeta: string | null;
  sede: string | null;
  valor_dia: string;
  estado: EstadoSalida;
  observacion: string;
  reportado: boolean;
  /** B10: valor de la novedad (0 si no tiene). */
  valor_novedad: string;
  /** B6/B7: la novedad como objeto (para verla antes de borrarla) o null. */
  novedad_detalle: {
    tipo: TipoNovedad;
    valor: string;
    descripcion: string;
  } | null;
  /** B10: valor_dia ± novedad — única implementación determinista. */
  total_a_pagar: string;
  /** B15: ¿el usuario actual puede gestionar esta fila (jefe/programación)? */
  puede_gestionar: boolean;
  creado_en: string;
}

/** Alta S6 — conserva los nombres legacy del form para el contrato del kiosco. */
export interface RegistrarSalidaPayload {
  fecha_salida: string;
  vehiculo: number;
  /** Cédula del personal que sale, o 'disponible'. */
  movil_sale: string;
  cc_asignada?: string;
  area?: string;
  carpeta?: string;
  sede?: string;
  observacion?: string;
  valor_dia?: string;
}

export interface Novedad {
  id: number;
  salida: number;
  tipo: TipoNovedad;
  valor: string;
  descripcion: string;
}

export interface SalidaHistorial {
  id: number;
  estado: EstadoSalida;
  motivo: string;
  fecha_cambio: string;
  creado_por: number | null;
  creado_por_cedula: string | null;
}

// ---------------------------------------------------------------------------
// Reporte fotográfico diario (F3/B3)
// ---------------------------------------------------------------------------

export interface ReporteFotoImagen {
  id: number;
  /** URL ya servida por Django (`MEDIA_URL`); no hace falta armar nada. */
  imagen: string;
  nombre_original: string;
}

export interface ReporteFotografico {
  id: number;
  /** Placa resuelta en servidor (el backoffice piensa en placas, no en PKs). */
  placa: string;
  /** `YYYY-MM-DD`. */
  fecha: string;
  /** `HH:MM:SS` — hora Colombia, dentro de la ventana 10:00–16:00. */
  hora: string;
  ot_actividad: string | null;
  responsable_cedula: string;
  responsable_nombre: string;
  /** Resultado de la validación OT-específica (agenda del día). */
  validacion_ot: Record<string, unknown>;
  /** Georreferencia del móvil (lat/lon/precisión) o null. */
  location: Record<string, number | string> | null;
  observaciones: string;
  imagenes: ReporteFotoImagen[];
  creado_en: string;
}

/** Filtros de `GET /transporte/reportes-fotograficos/`. */
export interface FiltrosReporteFoto {
  /** `YYYY-MM-DD` o vacío. */
  desde: string;
  hasta: string;
  /** Placa o pk; el servidor acepta cualquiera de los dos. */
  vehiculo: string;
}

/** Respuesta de `POST .../validar-agenda/` (desempaquetada por el servicio). */
export interface ResultadoAgendaReporte {
  tiene_agenda: boolean;
  /** `area_exenta` (no exige agenda) · `agenda` · `sin_identidad`. */
  origen: string;
  agendas: Array<Record<string, unknown>>;
  /** Vacío cuando `tiene_agenda` es true. Es el texto que ve el usuario. */
  msg: string;
  fecha?: string;
  /** Solo si se envió `ot_actividad`: match OT-específica del día. */
  ot?: {
    valida: boolean;
    origen: string;
    ot: string;
    msg: string;
  };
}

/** Lo que devuelve `GET .../vehiculo-placa/?placa=` (desempaquetado). */
export interface VehiculoResuelto {
  placa: string;
  tipo_vehiculo: string;
  marca: string;
  referencia: string;
  ciudad: string;
}

// ---------------------------------------------------------------------------
// Respuestas de acciones del backoffice (B4) y del kiosco (S1–S6)
// ---------------------------------------------------------------------------

export interface RespuestaAccion {
  detalle?: string;
  [clave: string]: unknown;
}

export interface ResultadoValidacionSalida {
  ok: boolean;
  detalle?: string;
  [clave: string]: unknown;
}
