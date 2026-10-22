// src/services/transporte.service.ts
//
// Cliente HTTP del módulo Transporte. Un método por endpoint del backend
// (apps/transporte/urls.py), con la URL exacta y el tipo de respuesta.
//
// Los nombres de los métodos replican los de DRF/`url_path` para que el
// enlace backend ↔ front sea un espejo sin interpretación.

import api from "@/lib/api";
import {
  normalizarPagina,
  obtenerTodasLasPaginas,
  type RespuestaPaginada,
} from "@/lib/paginas";
import type {
  Conductor,
  ConductorListado,
  CuentaCobroParams,
  DatosBancariosVehiculo,
  DocumentoVehiculo,
  FiltrosInformeArea,
  FiltrosInformeMensual,
  InformeArea,
  InformeAreasMes,
  InformeAreasPeriodo,
  InformeDia,
  InformeLiquidacion,
  InformeNomina,
  InformeSeriesChart,
  Mantenimiento,
  Novedad,
  PeriodoInforme,
  RegistrarSalidaPayload,
  ReporteFotografico,
  RespuestaAccion,
  ResultadoAgendaReporte,
  ResultadoValidacionSalida,
  Salida,
  SalidaHistorial,
  SerieChartParams,
  Vehiculo,
  VehiculoListado,
  VehiculoPayload,
  VehiculoResuelto,
} from "@/types/transporte.types";

// El prefijo es único en la app; centralizarlo evita divergencias.
const BASE = "/transporte";

// Re-exportados desde lib/paginas para no romper imports existentes.
export type { RespuestaPaginada } from "@/lib/paginas";

type ParamsBusqueda = Record<string, string | number | boolean | undefined>;

export const transporteService = {
  // ==========================================================================
  // Conductores (F2) — transporte_base_conductores
  // ==========================================================================

  /**
   * F2: catálogo completo. Usa `obtenerTodasLasPaginas` porque el filtrado
   * ocurre en el cliente (con 50 filas/página la tabla quedaría truncada).
   */
  getConductores: async (
    params?: ParamsBusqueda,
  ): Promise<ConductorListado[]> =>
    obtenerTodasLasPaginas<ConductorListado>(
      `${BASE}/conductores/`,
      params,
    ),

  getConductor: async (id: number): Promise<Conductor> => {
    const res = await api.get(`${BASE}/conductores/${id}/`);
    return res.data;
  },

  crearConductor: async (payload: Partial<Conductor>): Promise<Conductor> => {
    const res = await api.post(`${BASE}/conductores/`, payload);
    return res.data;
  },

  actualizarConductor: async (
    id: number,
    payload: Partial<Conductor>,
  ): Promise<Conductor> => {
    const res = await api.put(`${BASE}/conductores/${id}/`, payload);
    return res.data;
  },

  /**
   * Baja lógica (el legacy borraba el registro y perdía el historial).
   * El backend EXIGE `fecha_egreso` (§5.4), así que se envía en el cuerpo.
   */
  inactivarConductor: async (
    id: number,
    fechaEgreso: string,
  ): Promise<Conductor> => {
    const res = await api.post(`${BASE}/conductores/${id}/inactivar/`, {
      fecha_egreso: fechaEgreso,
    });
    return res.data;
  },

  // ==========================================================================
  // Vehículos / Flota (F2) — transportadores_vehiculos
  // ==========================================================================

  /**
   * Listado completo (`VehiculoListSerializer`), apto para la tabla de flota.
   * Trae TODAS las páginas (el filtrado es en cliente) y acepta `?search=`
   * (DRF SearchFilter) y los filtros del viewset.
   */
  getVehiculos: async (
    params?: ParamsBusqueda,
  ): Promise<VehiculoListado[]> =>
    obtenerTodasLasPaginas<VehiculoListado>(`${BASE}/vehiculos/`, params),

  getVehiculo: async (id: number): Promise<Vehiculo> => {
    const res = await api.get(`${BASE}/vehiculos/${id}/`);
    return res.data;
  },

  crearVehiculo: async (payload: VehiculoPayload): Promise<Vehiculo> => {
    const res = await api.post(`${BASE}/vehiculos/`, payload);
    return res.data;
  },

  actualizarVehiculo: async (
    id: number,
    payload: Partial<VehiculoPayload>,
  ): Promise<Vehiculo> => {
    const res = await api.put(`${BASE}/vehiculos/${id}/`, payload);
    return res.data;
  },

  inactivarVehiculo: async (id: number): Promise<RespuestaAccion> => {
    const res = await api.delete(`${BASE}/vehiculos/${id}/`);
    return res.data;
  },

  /**
   * E1 — catálogo operativo que reemplaza `get_vehiculos_transp`.
   * El semáforo SOAT/CDA viene calculado EN SERVIDOR (no aritmética en JS).
   */
  getCatalogoOperativo: async (): Promise<VehiculoListado[]> => {
    const res = await api.get(`${BASE}/vehiculos/catalogo-operativo/`);
    return normalizarPagina<VehiculoListado>(res.data).results;
  },

  /** T8: ficha de un vehículo con sus documentos, bancarios y mantenimientos. */
  getResumenVehiculo: async (id: number): Promise<VehiculoResumen> => {
    const res = await api.get(`${BASE}/vehiculos/${id}/resumen/`);
    return res.data;
  },

  /** T2: sube un documento (SOAT/CDA/matrícula/foto). Multipart. */
  subirDocumentoVehiculo: async (
    id: number,
    formData: FormData,
  ): Promise<DocumentoVehiculo> => {
    const res = await api.post(`${BASE}/vehiculos/${id}/documentos/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  },

  /** T3: importa datos bancarios (JSON `datos.bancarios[]` del legacy). */
  importarBancarios: async (
    payload: { vehiculo: number; bancarios: Partial<DatosBancariosVehiculo>[] },
  ): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/vehiculos/importar-bancarios/`, payload);
    return res.data;
  },

  /** T5: URL del PNG del código QR (codifica la placa, D-A8). */
  urlQrVehiculo: (id: number): string => `${BASE}/vehiculos/${id}/qr.png/`,

  // ==========================================================================
  // Salidas (F3/B2 + F4/B4) — transporte_registro_salida
  // ==========================================================================

  /**
   * B1: listado de salidas. Acepta `?fecha=`, `?desde=`, `?hasta=`,
   * `?estado=`, `?area=`, `?vehiculo=` y `?search=`.
   */
  getSalidas: async (params?: ParamsBusqueda): Promise<Salida[]> => {
    const res = await api.get(`${BASE}/salidas/`, { params });
    return normalizarPagina<Salida>(res.data).results;
  },

  /**
   * B1 con paginación server-side: devuelve `count` (total REAL del filtro)
   * junto con SOLO la página pedida. Es distinto de `getSalidas` porque con
   * ~250 mil salidas no se puede traer todo y filtrar en el cliente: aquí
   * quien pagina, filtra y ordena es el servidor.
   *
   * `count` es lo que alimenta el `pageCount` del DataTable (`manualPagination`).
   */
  getSalidasPaginado: async (
    params?: ParamsBusqueda,
  ): Promise<RespuestaPaginada<Salida>> => {
    const res = await api.get(`${BASE}/salidas/`, { params });
    return normalizarPagina<Salida>(res.data);
  },

  getSalida: async (id: number): Promise<Salida> => {
    const res = await api.get(`${BASE}/salidas/${id}/`);
    return res.data;
  },

  /**
   * S6: alta de salida. El contrato conserva los nombres legacy del form
   * (`movil_sale`, `cc_asignada`) para que el kiosco sea reconocible.
   */
  registrarSalida: async (payload: RegistrarSalidaPayload): Promise<Salida> => {
    const res = await api.post(`${BASE}/salidas/`, payload);
    return res.data;
  },

  /** B5: baja lógica (estado ELIMINADO; el registro se conserva). */
  eliminarSalida: async (id: number): Promise<RespuestaAccion> => {
    const res = await api.delete(`${BASE}/salidas/${id}/`);
    return res.data;
  },

  /** B12: validación masiva de salidas REPORTADO. */
  aprobarLote: async (ids: number[]): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/salidas/aprobar-lote/`, { ids });
    return res.data;
  },

  /** B4: aprobación individual (REPORTADO → APROBADO). */
  aprobarSalida: async (id: number): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/salidas/${id}/aprobar/`);
    return res.data;
  },

  /** B13: rechazo con motivo OBLIGATORIO (el backend lo exige). */
  rechazarSalida: async (id: number, motivo: string): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/salidas/${id}/rechazar/`, { motivo });
    return res.data;
  },

  /** D-A11: cierre de validación individual (APROBADO → VALIDADO). */
  validarSalida: async (id: number): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/salidas/${id}/validar/`);
    return res.data;
  },

  /** B6/B7: alta o borrado de novedad (ADICIONAL/DESCUENTO; una por salida). */
  guardarNovedad: async (
    id: number,
    payload: { tipo: string; valor: string; descripcion: string },
  ): Promise<Novedad> => {
    const res = await api.post(`${BASE}/salidas/${id}/novedad/`, payload);
    return res.data;
  },

  eliminarNovedad: async (id: number): Promise<RespuestaAccion> => {
    const res = await api.delete(`${BASE}/salidas/${id}/novedad/`);
    return res.data;
  },

  /** §7.2: trazabilidad 1:N (reemplaza el JSON `historial` longtext). */
  getHistorialSalida: async (id: number): Promise<SalidaHistorial[]> => {
    const res = await api.get(`${BASE}/salidas/${id}/historial/`);
    return normalizarPagina<SalidaHistorial>(res.data).results;
  },

  /** Exporta el listado filtrado (blob, para descarga directa). */
  exportarSalidas: async (params?: ParamsBusqueda): Promise<Blob> => {
    const res = await api.get(`${BASE}/salidas/export/`, {
      params,
      responseType: "blob",
    });
    return res.data as Blob;
  },

  // ==========================================================================
  // Kiosco (S1–S6) — consulta en terminal
  // ==========================================================================

  /** S1/S4: identifica vehículo por placa o por contenido del QR. */
  escanearQr: async (contenido: string): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/kiosco/escanear/`, { contenido });
    return res.data;
  },

  /** Alias de compatibilidad con el form legacy del kiosco. */
  identificarVehiculo: async (payload: {
    placa?: string;
    qr?: string;
  }): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/kiosco/identificar/`, payload);
    return res.data;
  },

  getVehiculoKiosco: async (placa: string): Promise<RespuestaAccion> => {
    const res = await api.get(`${BASE}/kiosco/vehiculo/${encodeURIComponent(placa)}/`);
    return res.data;
  },

  /** S3: pre-chequeo de fecha/vehículo/móvil ANTES del alta S6. */
  validarKiosco: async (payload: {
    fecha: string;
    vehiculo: number;
    movil_sale?: string;
  }): Promise<ResultadoValidacionSalida> => {
    const res = await api.post(`${BASE}/kiosco/validar/`, payload);
    return res.data;
  },

  // ==========================================================================
  // Reporte fotográfico (F3/B3)
  // ==========================================================================

  /**
   * F3/B3: alta de reporte con 1..5 imágenes.
   *
   * DEBE ir en `multipart`: el backend usa `request.data.getlist("imagenes")`
   * para recibir la lista, y con un JSON `[]` llegaría como un único string.
   *
   * Además el backend envuelve la respuesta en `{ok, data}` (contrato de las
   * acciones), así que aquí se desempaqueta: quien llama recibe el reporte
   * y no tiene que saber cómo envuelve cada endpoint su retorno.
   */
  guardarReporteFotografico: async (payload: {
    placa: string;
    imagenes: File[];
    ot_actividad?: string;
    observaciones?: string;
    location?: Record<string, unknown>;
  }): Promise<ReporteFotografico> => {
    const formulario = new FormData();
    formulario.append("placa", payload.placa);
    for (const imagen of payload.imagenes) {
      formulario.append("imagenes", imagen);
    }
    if (payload.ot_actividad) {
      formulario.append("ot_actividad", payload.ot_actividad);
    }
    if (payload.observaciones) {
      formulario.append("observaciones", payload.observaciones);
    }
    if (payload.location) {
      // El backend hace `json.loads(location)`: viaja como string.
      formulario.append("location", JSON.stringify(payload.location));
    }

    const res = await api.post(`${BASE}/reportes-fotograficos/`, formulario, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return (res.data?.data ?? res.data) as ReporteFotografico;
  },

  /** Listado paginado (server-side) para la tabla del backoffice. */
  getReportesPaginado: async (
    params?: ParamsBusqueda,
  ): Promise<RespuestaPaginada<ReporteFotografico>> => {
    const res = await api.get(`${BASE}/reportes-fotograficos/`, { params });
    return normalizarPagina<ReporteFotografico>(res.data);
  },

  /** B3 #1: pre-chequeo de agenda (y de OT-específica si se envía OT). */
  validarAgendaReporte: async (payload: {
    fecha: string;
    ot_actividad?: string;
  }): Promise<ResultadoAgendaReporte> => {
    const res = await api.post(
      `${BASE}/reportes-fotograficos/validar-agenda/`,
      payload,
    );
    // `{ok, data}` → `data`.
    return (res.data?.data ?? res.data) as ResultadoAgendaReporte;
  },

  /** Resuelve la placa a los datos del vehículo activo (para el modal). */
  getVehiculoPorPlaca: async (placa: string): Promise<VehiculoResuelto> => {
    const res = await api.get(`${BASE}/reportes-fotograficos/vehiculo-placa/`, {
      params: { placa },
    });
    const envuelto = res.data?.data ?? res.data;
    return (envuelto?.vehiculo ?? envuelto) as VehiculoResuelto;
  },

  // ==========================================================================
  // Informes (F5) — tablero de gestión
  //
  // Todos, salvo `mensual` y `cuenta-cobro`, envuelven su respuesta en
  // `{ok, data}` (contrato de las acciones de informes): aquí se
  // desempaqueta para que quien llama reciba el dato y no la envoltura.
  // `mensual` viene paginado de DRF y `cuenta-cobro` devuelve HTML.
  // ==========================================================================

  /**
   * F5-1: cuenta de cobro imprimible del alquiler (HTML).
   *
   * El importe y el pagador se calculan EN SERVIDOR desde las salidas del
   * mes: aquí solo viajan placa + periodo. El legacy recibía esos valores
   * en campos ocultos del formulario, manipulables desde el navegador.
   */
  getInformeCuentaCobro: async (params: CuentaCobroParams): Promise<string> => {
    const res = await api.get(`${BASE}/informes/cuenta-cobro/`, { params });
    return typeof res.data === "string" ? res.data : "";
  },

  /** F5-2: series del gráfico "Pagos por Mes, por Área" (sin año = histórico). */
  getSeriesChart: async (
    params?: SerieChartParams,
  ): Promise<InformeSeriesChart> => {
    const res = await api.get(`${BASE}/informes/series-chart/`, { params });
    return (res.data?.data ?? res.data) as InformeSeriesChart;
  },

  /**
   * F5-3: informe mensual día a día, paginado (server-side pagina y filtra).
   *
   * Es el ÚNICO de los 9 que no envuelve en `{ok, data}`: `mensual` usa
   * `get_paginated_response`, así que devuelve `{count, next, previous,
   * results}`. Las filas son `Salida` completas (con `centro_costos`, B11).
   *
   * `count` es el total REAL del filtro, útil para el paginador.
   */
  getInformeMensual: async (
    params: FiltrosInformeMensual & { page?: number; page_size?: number },
  ): Promise<RespuestaPaginada<Salida>> => {
    const res = await api.get(`${BASE}/informes/mensual/`, { params });
    return normalizarPagina<Salida>(res.data);
  },

  /** F5-7: agregado de UNA fecha, con desglose por área y por carpeta. */
  getInformeDia: async (params: { fecha: string }): Promise<InformeDia> => {
    const res = await api.get(`${BASE}/informes/dia/`, { params });
    return (res.data?.data ?? res.data) as InformeDia;
  },

  /** F5-7: áreas presentes en el periodo (para poblar el filtro del mes). */
  getInformeAreas: async (
    params: PeriodoInforme,
  ): Promise<InformeAreasPeriodo> => {
    const res = await api.get(`${BASE}/informes/areas/`, { params });
    return (res.data?.data ?? res.data) as InformeAreasPeriodo;
  },

  /**
   * F5-7: agregado del mes por área con desglose por carpetas.
   * `solo_aprobados` es el interruptor de la sábana (bloque "Mes").
   */
  getInformeArea: async (params: FiltrosInformeArea): Promise<InformeArea> => {
    const res = await api.get(`${BASE}/informes/area/`, { params });
    return (res.data?.data ?? res.data) as InformeArea;
  },

  /** F5-7: matriz área × meses del año (base del gráfico y de Día a Día). */
  getInformeAreasMes: async (params: {
    anio: number;
  }): Promise<InformeAreasMes> => {
    const res = await api.get(`${BASE}/informes/areas-mes/`, { params });
    return (res.data?.data ?? res.data) as InformeAreasMes;
  },

  /**
   * F5-7: nómina del mes por (carpeta, placa). Excluye REPORTADO/ELIMINADO;
   * retefuente 1 %; pagador desde los datos bancarios del vehículo.
   */
  getInformeNomina: async (params: PeriodoInforme): Promise<InformeNomina> => {
    const res = await api.get(`${BASE}/informes/nomina/`, { params });
    return (res.data?.data ?? res.data) as InformeNomina;
  },

  /**
   * F5-7: liquidación por placa (UNA fila por vehículo). Mismos criterios
   * que nómina; el importe a pagar es `pagar`.
   */
  getInformeLiquidacion: async (
    params: PeriodoInforme,
  ): Promise<InformeLiquidacion> => {
    const res = await api.get(`${BASE}/informes/liquidacion/`, { params });
    return (res.data?.data ?? res.data) as InformeLiquidacion;
  },

  // ==========================================================================
  // Liquidaciones / sábanas (A2)
  // ==========================================================================

  getLiquidaciones: async (params?: ParamsBusqueda): Promise<unknown[]> => {
    const res = await api.get(`${BASE}/liquidaciones/`, { params });
    return normalizarPagina<unknown>(res.data).results;
  },

  getSabana: async (params: ParamsBusqueda): Promise<unknown> => {
    const res = await api.get(`${BASE}/liquidaciones/sabana/`, { params });
    return res.data;
  },

  getPagoMensual: async (params: ParamsBusqueda): Promise<unknown> => {
    const res = await api.get(`${BASE}/liquidaciones/pago-mensual/`, { params });
    return res.data;
  },

  getProntoPago: async (params: ParamsBusqueda): Promise<unknown> => {
    const res = await api.get(`${BASE}/liquidaciones/pronto-pago/`, { params });
    return res.data;
  },

  /** D3: genera el consecutivo del período (atómico en servidor). */
  generarConsecutivo: async (payload: {
    mes: number;
    anio: number;
  }): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/liquidaciones/consecutivo/`, payload);
    return res.data;
  },

  /** D3: registra el pago del período (queda cerrado). */
  registrarPago: async (payload: {
    mes: number;
    anio: number;
  }): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/liquidaciones/pago/`, payload);
    return res.data;
  },

  // ==========================================================================
  // Planillas (F5-6) — Planilla Oficial de Salida F-104
  // ==========================================================================

  /**
   * S5/CR-11: genera la planilla con consecutivo atómico y QR en disco.
   * `alcance`: PLACA | PROPIO | EXTERNO | RENTING | TODAS.
   */
  generarPlanilla: async (payload: {
    fecha: string;
    alcance: string;
  }): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/planillas/generar/`, payload);
    return res.data;
  },

  /** P1: HTML imprimible de la hoja de vehículo (F-104). */
  getFormatoPlanilla: async (payload: {
    fecha: string;
    alcance?: string;
  }): Promise<string> => {
    const res = await api.post(`${BASE}/planillas/formato/`, payload);
    return typeof res.data === "string" ? res.data : (res.data?.html ?? "");
  },

  // ==========================================================================
  // Parámetros (A1)
  // ==========================================================================

  getCierres: async (params?: ParamsBusqueda): Promise<unknown[]> => {
    const res = await api.get(`${BASE}/parametros/cierres/`, { params });
    return normalizarPagina<unknown>(res.data).results;
  },

  getJefesValidadores: async (params?: ParamsBusqueda): Promise<unknown[]> => {
    const res = await api.get(`${BASE}/parametros/jefes/`, { params });
    return normalizarPagina<unknown>(res.data).results;
  },

  // ==========================================================================
  // Validaciones de cierre mensual (F4)
  // ==========================================================================

  getValidaciones: async (params?: ParamsBusqueda): Promise<unknown[]> => {
    const res = await api.get(`${BASE}/validaciones/`, { params });
    return normalizarPagina<unknown>(res.data).results;
  },

  // ==========================================================================
  // WFM (F5-5)
  // ==========================================================================

  validarWfm: async (payload: unknown): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/wfm/validar/`, payload);
    return res.data;
  },

  crearJobWfm: async (payload: unknown): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/wfm/crear-job/`, payload);
    return res.data;
  },

  estadoJobWfm: async (payload: { job_id: number }): Promise<RespuestaAccion> => {
    const res = await api.post(`${BASE}/wfm/estado-job/`, payload);
    return res.data;
  },

  // ==========================================================================
  // Permisos (E3/CR-8) — reemplaza las cédulas hardcodeadas del legacy
  // ==========================================================================

  /**
   * Estado de permisos del usuario actual (`puede_programar`,
   * `permiso_especial`, `editar_tras_cierre`).
   */
  getEstadoPermisos: async (): Promise<EstadoPermisos> => {
    const res = await api.get(`${BASE}/permisos/estado/`);
    return res.data;
  },
};

// ---------------------------------------------------------------------------
// Tipos derivados de respuestas que no tienen modelo propio en el front
// ---------------------------------------------------------------------------

/** Ficha de vehículo (acción `resumen`): vehículo + colecciones anidadas. */
export interface VehiculoResumen {
  vehiculo: Vehiculo;
  documentos: DocumentoVehiculo[];
  datos_bancarios: DatosBancariosVehiculo[];
  mantenimientos: Mantenimiento[];
}

/** Permisos granulares del usuario (CR-8). */
export interface EstadoPermisos {
  puede_programar: boolean;
  permiso_especial: boolean;
  editar_tras_cierre: boolean;
  es_superuser: boolean;
}

export default transporteService;
