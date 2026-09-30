// src/types/agenda.types.ts

export type SedeOption = "medellin" | "monteria" | "sincelejo" | "";

export interface AgendaObservacionesDia {
  estado?: string;
  color?: string;
  [key: string]: any;
}

export interface AgendaItemDatos {
  empleado_id?: string | number;
  cedula?: string;
  area?: string;
  carpeta?: string;
  sede?: string;
  actividad?: string;
  nombre_act?: string;
  legacy_actividad_id?: string | number;
  legacy_estado?: string;
  legacy_responsable_nombre?: string;
  legacy_responsable_movil?: string;
  detalle_descripcion?: string;
  ubicacion_direccion?: string;
  ubicacion_zona?: string;
  ubicacion_nodo?: string;
  longitud?: string;
  latitud?: string;
  color?: string;
  [key: string]: any;
}

export interface AgendaItem {
  id?: number | string;
  empleado_id?: string | number;
  cedula: string;
  fecha: string;
  fecha_inicio: string;
  fecha_fin: string;
  fecha_inicio2?: string;
  fecha_fin2?: string;
  sede?: string;
  area?: string;
  carpeta?: string;
  nombre_act: string;
  nombre?: string;
  responsable_nombre?: string;
  responsable_link_foto?: string;
  link_foto?: string;
  tipo_trabajo?: string;
  actividad: string;
  actividad_id?: number;
  actividad_estado?: string;
  observacion?: string;
  ot?: string;
  estado?: string;
  color?: string;
  datos?: AgendaItemDatos;
  observaciones_dia?: AgendaObservacionesDia;
  legacy_actividad_id?: string | number;
  legacy_estado?: string;
  legacy_responsable_nombre?: string;
  legacy_responsable_movil?: string;
  detalle_descripcion?: string;
  ubicacion_direccion?: string;
  direccion?: string;
  ubicacion_zona?: string;
  zona?: string;
  ubicacion_nodo?: string;
  nodo?: string;
  latitud?: string;
  longitud?: string;
  edit?: string;
  fecha_edit?: string;
}

export interface TecnicoActivoAgenda {
  id?: number | null;
  empleado_id?: number | null;
  cedula: string;
  nombre: string;
  sede: string;
  area: string;
  carpeta: string;
  cargo?: string;
  movil?: string;
  link_foto?: string | null;
}

export interface FiltrosAgendaState {
  sede: SedeOption;
  mes: string;
  yyyy: string;
  cedula: string;
  actividad: string;
  nombre: string;
  area: string;
  carpeta: string;
}

export interface ParametroCarpetaColor {
  param: string;
  color: string;
  nombre?: string;
  label?: string;
}

export interface ActividadOtConsulta {
  id: number;
  ot: string;
  estado: string;
  fecha_inicio: string | null;
  fecha_fin_estimado: string | null;
  tipo_trabajo: string;
  descripcion: string;
  direccion: string;
  zona: string;
  nodo: string;
  longitud: string;
  latitud: string;
  responsable_id: number;
  responsable_nombre: string;
  responsable_area: string;
  responsable_carpeta: string;
  responsable_movil: string;
  responsable_link_foto?: string;
}

export interface FilaResultadoImportacion {
  fila: number;
  cedula: string;
  ot: string;
  fecha_inicio: string;
  fecha_fin: string;
  success: boolean;
  mensaje: string;
}

export interface ResultadoImportacionCsv {
  success: boolean;
  total_filas: number;
  exitosos: number;
  fallidos: number;
  resultados: FilaResultadoImportacion[];
  msg?: string;
}
