// src/services/agenda.service.ts
import api from "@/lib/api";
import {
  ActividadOtConsulta,
  AgendaItem,
  ParametroCarpetaColor,
  ResultadoImportacionCsv,
  TecnicoActivoAgenda,
} from "@/types/agenda.types";

export const agendaService = {
  /**
   * Obtiene todos los agendamientos del mes y año dados.
   */
  getAgendasMes: async (mes: string, yyyy: string, sede?: string): Promise<any[]> => {
    const res = await api.get("/operaciones/agenda/mes/", {
      params: { mes, yyyy, ...(sede ? { sede } : {}) },
    });
    return res.data;
  },

  /**
   * Guarda o actualiza un agendamiento en operaciones_agenda.
   */
  guardarAgenda: async (payload: {
    id?: number | string;
    actividad_id?: number;
    responsable_id?: number;
    fecha_inicio?: string;
    fecha_fin?: string;
    sede?: string;
    color_hex?: string;
    observacion?: string;
    estado?: string;
    tipo_trabajo?: string;
    descripcion?: string;
    direccion?: string;
    zona?: string;
    nodo?: string;
    longitud?: string;
    latitud?: string;
    data_form?: Record<string, any>;
    data_param?: Record<string, any>;
    data_anterior?: Record<string, any> | null;
  }) => {
    const res = await api.post("/operaciones/agenda/guardar/", payload);
    return res.data;
  },

  /**
   * Elimina un agendamiento (Soft-delete).
   */
  eliminarAgenda: async (agendaId: number | string) => {
    const res = await api.delete(`/operaciones/agenda/${agendaId}/eliminar/`);
    return res.data;
  },

  /**
   * Lista todos los técnicos registrados y activos en agenda.
   */
  getTecnicosActivos: async (sede?: string): Promise<TecnicoActivoAgenda[]> => {
    const res = await api.get("/operaciones/agenda/tecnicos-activos/", {
      params: sede ? { sede } : {},
    });
    return res.data;
  },


  /**
   * Busca información de una OT para autocompletar el formulario de agenda.
   */
  buscarActividadPorOt: async (ot: string): Promise<{ success: boolean; data: ActividadOtConsulta }> => {
    const res = await api.get(`/operaciones/agenda/actividad-ot/${encodeURIComponent(ot)}/`);
    return res.data;
  },

  /**
   * Obtiene los colores / parámetros configurados para una carpeta.
   */
  getParametrosCarpeta: async (carpetaId: number | string) => {
    const res = await api.get(`/operaciones/agenda/parametros-carpeta/${carpetaId}/`);
    return res.data;
  },

  /**
   * Guarda los parámetros de colores para una sede y carpeta.
   */
  saveParametrosCarpeta: async (carpetaId: number | string, sede: string, dataParam: ParametroCarpetaColor[]) => {
    const res = await api.post(`/operaciones/agenda/parametros-carpeta/${carpetaId}/`, {
      sede,
      data_param: dataParam,
    });
    return res.data;
  },

  /**
   * Elimina un color / parámetro de la carpeta.
   */
  eliminarParametroCarpeta: async (carpetaId: number | string, sede: string, paramId: string) => {
    const res = await api.post(`/operaciones/agenda/eliminar-parametro/${carpetaId}/`, {
      sede,
      param_id: paramId,
    });
    return res.data;
  },

  /**
   * Sube e importa un archivo CSV masivo.
   */
  importarCsv: async (file: File): Promise<ResultadoImportacionCsv> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await api.post("/operaciones/agenda/importar-csv/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return res.data;
  },
};
