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
  /** B11: centro de costos de la carpeta, resuelto EN SERVIDOR con
   *  fallback `'Sin asignar'` (literal del legacy). */
  centro_costos: string;
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
// Informes / sábana (F5) — services/informe_service.py
// ---------------------------------------------------------------------------
//
// ⚠ FORMATO DEL DINERO: conviven dos formas según cómo serialize el backend.
//
//  · Agregados (`dia`, `area`, `areas-mes`, `nomina`, `liquidacion`):
//    `InformeService` devuelve `Decimal` CRUDO dentro de `Response()` y el
//    encoder de DRF lo convierte en **number**
//    (`rest_framework/utils/encoders.py:43-45`).
//  · Filas de salida (`mensual`): pasan por `SalidaSerializer`, cuyo
//    `DecimalField` los envía como **string**.
//
// Por eso aquí los importes de agregado son `number` y los de `Salida`
// siguen siendo `string`. Quien formatee debe saber cuál es cuál.
// (Decisión pendiente: unificar a string en backend.)

/** Parámetros de los endpoints con periodo (mes/año). */
export interface PeriodoInforme {
  mes: number;
  anio: number;
}

/** `GET /informes/mensual/` — periodo + filtros server-side (§5.7). */
export interface FiltrosInformeMensual extends PeriodoInforme {
  estado?: string;
  sede?: string;
  area?: string;
  carpeta?: string;
  search?: string;
}

/** `GET /informes/cuenta-cobro/` — entrada mínima (F5-1). */
export interface CuentaCobroParams extends PeriodoInforme {
  /** Mayúsculas; el backend la normaliza. */
  placa: string;
}

/** `GET /informes/series-chart/` — año opcional (sin año = histórico). */
export interface SerieChartParams {
  anio?: number;
}

/** `GET /informes/area/` — periodo + interruptor "Aprobados" de la sábana. */
export interface FiltrosInformeArea extends PeriodoInforme {
  /** true = los TOTALES solo suman APROBADO/VALIDADO (ver `arr_estado`). */
  solo_aprobados?: boolean;
}

/** Contador de salidas + importe acumulado en UN estado. */
export interface ContadorEstadoInforme {
  cnt: number;
  /** Decimal crudo → llega como número. Formatear en el front. */
  valor: number;
}

/**
 * `arr_estado` de un bloque agregado. El legacy llamaba `pendiente` a
 * REPORTADO; el backend usa el nombre real del estado.
 */
export interface DesgloseEstadosInforme {
  aprobado: ContadorEstadoInforme;
  validado: ContadorEstadoInforme;
  reportado: ContadorEstadoInforme;
  rechazado: ContadorEstadoInforme;
  /** Suma de los 4 anteriores (todas las filas del bloque). */
  total: ContadorEstadoInforme;
}

/**
 * Contadores de un bloque de agregado (`_bloque_vacio`).
 *
 * RENTING se cuenta APARTE: el legacy lo mezclaba dentro de `propios`.
 * El legacy también pintaba `Ttl_Pro`/`Ttl_Ext` (dinero propio/externo por
 * separado) y el backend NO los expone todavía — hueco E del informe F5.
 */
export interface BloqueAgregadoInforme {
  propios: number;
  renting: number;
  externos: number;
  total_vehi: number;
  /** Σ `total_a_pagar` (valor_dia ± novedad) del bloque. */
  total_dia: number;
  /**
   * Desglose por estado. SIEMPRE refleja todas las filas, aunque
   * `solo_aprobados` haya restringido `total_dia` y los contadores.
   */
  arr_estado: DesgloseEstadosInforme;
}

/** Fila del desglose por carpetas dentro de un área. */
export interface CarpetaInforme extends BloqueAgregadoInforme {
  /** `'SIN CARPETA'` si la salida no traía carpeta. */
  carpeta: string;
}

/** Área con su desglose por carpetas (bloques Día y Mes). */
export interface AreaInforme extends BloqueAgregadoInforme {
  /** En mayúsculas; `'SIN AREA'` si la salida no traía área. */
  area: string;
  carpetas: CarpetaInforme[];
}

/** `GET /informes/dia/?fecha=` → data del agregado de UNA fecha. */
export interface InformeDia {
  /** `YYYY-MM-DD`. */
  fecha: string;
  areas: AreaInforme[];
}

/** `GET /informes/area/?mes=&anio=&solo_aprobados=` → data del mes. */
export interface InformeArea {
  mes: number;
  anio: number;
  areas: AreaInforme[];
}

/** Fila de la matriz área × meses (solo los meses que tienen salidas). */
export interface MesAreaInforme {
  mes: number;
  propios: number;
  renting: number;
  externos: number;
  total_vehi: number;
  total_dia: number;
}

export interface AreaMatrizInforme {
  area: string;
  meses: MesAreaInforme[];
}

/** `GET /informes/areas-mes/?anio=` → data de la matriz del año. */
export interface InformeAreasMes {
  anio: number;
  areas: AreaMatrizInforme[];
}

/** `GET /informes/areas/?mes=&anio=` — áreas del periodo (poblar filtro). */
export interface InformeAreasPeriodo {
  areas: string[];
}

/**
 * Fila de la nómina del mes, agrupada por (carpeta, placa).
 * Excluye REPORTADO y ELIMINADO.
 */
export interface FilaNominaInforme {
  mes: number;
  placa: string;
  /** `'SIN CARPETA'` si la salida no traía carpeta. */
  carpeta: string;
  /**
   * B11: centro de costos de la carpeta. HOY VACÍO — `InformeService.nomina`
   * aún no consume `ParametrosService.centro_costos` aunque B11 ya existe
   * (deuda C del informe F5).
   */
  centro_costo: string;
  area: string;
  tipo_contrato: TipoContrato;
  /** Pagador leído del dato bancario vigente EN SERVIDOR (CR-13); sin dato
   *  bancario, el propietario del vehículo. */
  cedula_pago: string;
  nombre_pago: string;
  total_dias: number;
  /** `valor_dia` del PRIMER día del grupo (las novedades van en `valor_base`). */
  valor_dia: number;
  /** Σ `total_a_pagar` = valor_dia ± novedad, de todos los días del grupo. */
  valor_base: number;
  /** Estado de la PRIMERA salida del grupo (orden placa, fecha). */
  estado: EstadoSalida;
  observacion: string;
  /** Consecutivo mensual si ya fue generado (A2); vacío si no. */
  consecutivo: string;
  /** Retefuente 1 % de `valor_base`. */
  rte: number;
  /** `valor_base − rte`. */
  total_pagar: number;
}

/** `GET /informes/nomina/?mes=&anio=` → data de la nómina. */
export interface InformeNomina {
  mes: number;
  anio: number;
  filas: FilaNominaInforme[];
}

/** Fila de la liquidación por placa: UNA por vehículo del mes. */
export interface FilaLiquidacionInforme {
  placa: string;
  /** `'SIN PROPIETARIO'` si el vehículo no traía propietario. */
  propietario: string;
  tipo_contrato: TipoContrato;
  total_dias: number;
  valor_dia: number;
  valor_base: number;
  cedula_pago: string;
  nombre_pago: string;
  tipo_cuenta: string;
  banco: string;
  cuenta_pago: string;
  /** Consecutivo mensual si ya existe; vacío si no. */
  consecutivo: string;
  /** Retefuente 1 %. */
  rte: number;
  /** `valor_base − rte`. */
  pagar: number;
}

/** `GET /informes/liquidacion/?mes=&anio=` → data de la liquidación. */
export interface InformeLiquidacion {
  mes: number;
  anio: number;
  filas: FilaLiquidacionInforme[];
}

/** Punto del gráfico: `["<mes>/1/<año>", importe]` — eje X de tiempo. */
export type PuntoSerieInforme = [string, number];

/** Serie del gráfico "Pagos por Mes, por Área" (F5-2). */
export interface SerieInforme {
  /** Nombre del área. */
  name: string;
  /** Solo el área I&M: va al eje secundario (derecha). */
  yAxis?: "a2";
  /** Solo el área I&M: estilo de línea/marcador del eje secundario. */
  defaultPoint?: {
    type: string;
    marker: {
      size: number;
      type: string;
      outline: { color: string; width: number };
    };
  };
  points: PuntoSerieInforme[];
}

/** `GET /informes/series-chart/?anio=` → data del gráfico. */
export interface InformeSeriesChart {
  series: SerieInforme[];
}

/**
 * Datos que el backend calcula EN SERVIDOR para la cuenta de cobro (F5-1).
 *
 * El endpoint NO devuelve este objeto: devuelve el HTML ya renderizado
 * (que el navegador abre en pestaña nueva e imprime a PDF). El tipo
 * documenta qué contiene ese documento y será la forma de la impresión
 * múltiple cuando exista (hueco B3 del informe F5).
 */
export interface CuentaCobroInforme {
  placa: string;
  mes: number;
  anio: number;
  /** `'ENERO'` … `'DICIEMBRE'`. */
  nombre_mes: string;
  /** Último día del mes (texto "Del 01 de X al N de X"). */
  ultimo_dia: number;
  consecutivo: string;
  total_dias: number;
  valor_base: number;
  retefuente: number;
  pagar: number;
  cedula_pago: string;
  nombre_pago: string;
  tipo_cuenta: string;
  banco: string;
  cuenta_pago: string;
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

// ---------------------------------------------------------------------------
// Kiosco (S1-S6) — respuestas tipadas de /kiosco/
// ---------------------------------------------------------------------------

/** Respuesta del backend (contrato { ok, data | error }) para el kiosco. */
export interface KioscoRespuesta<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
}

/** Data dentro de POST /kiosco/identificar/ y GET /kiosco/vehiculo/{placa}/ */
export interface KioscoDatoVehiculo {
  vehiculo: Vehiculo;
  salida: Salida | null;
}

/** Resultado del pre-chequeo POST /kiosco/validar/ (S3) */
export interface KioscoResultadoValidacion {
  validable: boolean;
  duplicado_vehiculo: boolean;
  duplicado_movil: boolean;
  puede_registrar: boolean;
  mensaje: string;
  registro: Salida | null;
  salida: Salida | null;
}

// ---------------------------------------------------------------------------
// Planilla Oficial de Salida F-104 (F5-6 / S5 / CR-11)
// ---------------------------------------------------------------------------

export type AlcancePlanilla =
  | "PLACA"
  | "TODAS"
  | "PROPIO"
  | "EXTERNO"
  | "RENTING";

export interface SalidaDiaPlanilla {
  id: number;
  estado: string;
  conductor_cedula: string | null;
  tecnico_cedula: string | null;
  area: string | null;
  carpeta: string | null;
  observacion: string;
}

export interface ConductorPlanilla {
  cedula: string;
  nombre: string;
  celular: string;
  licencia_categoria: string | null;
  licencia_vencimiento: string | null;
}

export interface VehiculoPlanilla {
  vehiculo_id: number;
  placa: string;
  tipo_vehiculo: string;
  tipo_contrato: string;
  marca: string;
  referencia: string | null;
  modelo_anio: number;
  color: string | null;
  nombre_propietario: string;
  cedula_propietario: string;
  valor_dia_base: string | number;
  conductor: ConductorPlanilla | null;
  consecutivo: number;
  consecutivo_creado: boolean;
  mes: number;
  anio: number;
  ruta_qr: string | null;
  salidas_del_dia: SalidaDiaPlanilla[];
}

export interface PlanillaData {
  fecha: string;
  alcance: AlcancePlanilla;
  vehiculos: VehiculoPlanilla[];
}

export interface GenerarPlanillaPayload {
  fecha: string;
  alcance: AlcancePlanilla;
  placa?: string;
}

// ---------------------------------------------------------------------------
// Cierres de Validación Mensual por Área (F4 / B4 / ValidacionSalida)
// ---------------------------------------------------------------------------

export interface ValidacionSalida {
  id: number;
  area: string;
  mes: number;
  anio: number;
  datos?: Record<string, unknown>;
  creado_en: string;
  modificado_en: string;
}

export interface CerrarAreaPayload {
  area: string;
  mes: number;
  anio: number;
  datos?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Liquidaciones Financieras (A2 / D3 / D4 / CR-10)
// ---------------------------------------------------------------------------

export interface SabanaFila {
  vehiculo: number;
  placa: string;
  tipo_contrato: TipoContrato | string;
  conductor_cedula: string | null;
  valor_dia: string | number;
  dias: number;
  total: string | number;
  pagado: boolean;
  fecha_pago: string | null;
  total_liquidado: string | number;
}

export interface SabanaTotales {
  dias: number;
  total: string | number;
}

export interface SabanaLiquidacion {
  mes: number;
  anio: number;
  mes_aplicado: number;
  anio_aplicado: number;
  retroactivo: boolean;
  filas: SabanaFila[];
  totales: SabanaTotales;
}

export interface PagoVehiculoRegistro {
  id: number;
  vehiculo: number;
  placa: string;
  mes: number;
  anio: number;
  tipo: TipoPago | string;
  pagado: boolean;
  fecha_pago: string | null;
  total_liquidado: string | number;
  modificado_en: string;
}

export interface RegistrarPagoPayload {
  vehiculo: number;
  mes: number;
  anio: number;
  tipo?: TipoPago | string;
  pagado?: boolean;
  fecha_pago?: string;
  total_liquidado?: number | string;
}

export interface ConsecutivoLiquidacion {
  vehiculo: number;
  mes: number;
  anio: number;
  consecutivo: number;
  creado: boolean;
}



