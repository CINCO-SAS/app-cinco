import { Empleado } from "@/types/empleado";

// ─── Interfaces de Datos Específicos de Tipología 5 (Sistema Eléctrico MT/BT) ─

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
  descripcion: string;
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

export interface TransporteItem {
  id: string;
  tipo: string;
  codigo_sap: string;
  distancia_km: string;
  tiempo: string;
  descripcion: string;
  foto_antes_preview?: string;
  foto_antes_file?: File;
  foto_antes_nombre?: string;
  /** Título de la caja en el Excel. */
  foto_antes_descripcion?: string;
  foto_durante_preview?: string;
  foto_durante_file?: File;
  foto_durante_nombre?: string;
  /** Título de la caja en el Excel. */
  foto_durante_descripcion?: string;
  foto_despues_preview?: string;
  foto_despues_file?: File;
  foto_despues_nombre?: string;
  /** Título de la caja en el Excel. */
  foto_despues_descripcion?: string;
}

export interface JustificacionFotoItem {
  id: string;
  previewUrl?: string;
  file?: File;
  nombre?: string;
  /** Título de la caja en el Excel. */
  descripcion?: string;
}

export interface FormCapexTipologia5Data {
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

  // 3. Transportes
  transportes: TransporteItem[];

  // 4. Panorámica de la Torre y Plano EB a Mano Alzada
  foto_panoramica_preview?: string;
  foto_panoramica_file?: File;
  /** Título de la caja en el Excel. */
  foto_panoramica_descripcion?: string;
  foto_plano_preview?: string;
  foto_plano_file?: File;
  /** Título de la caja en el Excel. */
  foto_plano_descripcion?: string;
  plano_recomendacion_aliado: string;

  // 5. Resultados de Otras Actividades Fuera del Estándar
  texto_justificacion: string;
  fotos_justificacion: JustificacionFotoItem[];

  // 6. Recomendaciones de la Actividad
  recomendaciones_finales: string;
}
