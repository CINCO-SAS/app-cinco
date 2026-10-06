import { Empleado } from "@/types/empleado";

// ─── Interfaces de Datos Específicos de Tipología 1 ───────────────────────────

export interface InsumoSAPItem {
  id: string;
  texto_sap: string;
  codigo_sap: string;
  alcance: string;
  comentarios: string;
  cantidad_estandar: string;
  cantidad_real: string;
  unidad_medida: string;
  foto_preview?: string;
  foto_file?: File;
  foto_nombre?: string;
  /** Título de la caja en el Excel. */
  foto_descripcion?: string;
}

export interface ActividadMOItem {
  id: string;
  texto_sap: string;
  codigo_sap: string;
  alcance: string;
  comentarios: string;
  foto_antes_preview?: string;
  foto_antes_file?: File;
  foto_antes_nombre?: string;
  /** Título de la caja en el Excel. */
  foto_antes_descripcion?: string;
  foto_despues_preview?: string;
  foto_despues_file?: File;
  foto_despues_nombre?: string;
  /** Título de la caja en el Excel. */
  foto_despues_descripcion?: string;
}

export interface FilaMedidaSPT {
  id: string;
  distancia: string;
  medida_ohmio: string;
  resistividad: string;
}

export interface JustificacionFotoItem {
  id: string;
  previewUrl?: string;
  file?: File;
  nombre?: string;
  /** Título de la caja en el Excel. */
  descripcion?: string;
}

export interface FormCapexTipologia1Data {
  // Información General
  nombre_estacion: string;
  ot: string;
  fecha_inicio: string;
  fecha_fin: string;
  tipo_estacion: string;
  site_owner: string;
  responsable_ejecuta: Empleado | null;
  empresa: string;
  coordinador_aliado: string;

  // 1.- Inventario de Suministros
  insumos: InsumoSAPItem[];

  // 2.- MO - Actividades Estandarizadas
  actividades: ActividadMOItem[];
  descripcion_general_actividades: string;

  // 3. Transportes
  transporte_tipo: string;
  transporte_codigo_sap: string;
  transporte_distancia_km: string;
  transporte_tiempo_desplazamiento: string;
  transporte_descripcion: string;
  transporte_foto_antes?: string;
  transporte_foto_antes_file?: File;
  /** Título de la caja en el Excel. */
  transporte_foto_antes_descripcion?: string;
  transporte_foto_durante?: string;
  transporte_foto_durante_file?: File;
  /** Título de la caja en el Excel. */
  transporte_foto_durante_descripcion?: string;
  transporte_foto_despues?: string;
  transporte_foto_despues_file?: File;
  /** Título de la caja en el Excel. */
  transporte_foto_despues_descripcion?: string;

  // 4. Resultados de Reforma SPT
  spt_naturaleza_terreno_desc: string;
  spt_naturaleza_terreno_foto?: string;
  spt_naturaleza_terreno_foto_file?: File;
  /** Título de la caja en el Excel. */
  spt_naturaleza_terreno_foto_descripcion?: string;
  filas_spt: FilaMedidaSPT[];
  spt_recomendacion_aliado: string;

  // 5. Panorámica de la Torre y Plano EB
  foto_panoramica_preview?: string;
  foto_panoramica_file?: File;
  /** Título de la caja en el Excel. */
  foto_panoramica_descripcion?: string;
  foto_plano_preview?: string;
  foto_plano_file?: File;
  /** Título de la caja en el Excel. */
  foto_plano_descripcion?: string;
  plano_recomendacion_aliado: string;

  // 6. Actividades Fuera del Estándar
  otras_actividades_1: string;
  otras_actividades_2: string;
  otras_actividades_3: string;
  texto_justificacion_otras_actividades: string;
  fotos_justificacion: JustificacionFotoItem[];
  foto_soporte_matricula_preview?: string;
  foto_soporte_matricula_file?: File;
  /** Título de la caja en el Excel. */
  foto_soporte_matricula_descripcion?: string;
  matricula_nombre: string;
  matricula_numero: string;
  matricula_fecha: string;

  // 7. Recomendaciones y Cierre
  recomendaciones_finales: string;
  responsable_entrega_nombre: string;
  responsable_entrega_cedula: string;
  responsable_entrega_cargo: string;
  responsable_entrega_fecha: string;
  responsable_entrega_firma: string;

  aprobado_nombre: string;
  aprobado_cedula: string;
  aprobado_cargo: string;
  aprobado_fecha: string;
  aprobado_firma: string;
  observaciones_cierre: string;
}
