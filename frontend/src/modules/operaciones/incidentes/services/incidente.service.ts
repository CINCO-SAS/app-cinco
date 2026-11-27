import api from "@/lib/api";
import { IncidenteBusquedaResponse, IncidenteFuente } from "../types";

const BASE_URL = "/operaciones/incidentes";

export interface BuscarIncidenteParams {
  inc: string;
  fuente?: string;
  refresh?: boolean;
}

export const incidenteService = {
  async listarFuentes(): Promise<IncidenteFuente[]> {
    const res = await api.get<{ success: boolean; fuentes: IncidenteFuente[] }>(
      `${BASE_URL}/fuentes/`,
    );
    return res.data?.fuentes || [];
  },

  async buscarPorInc({
    inc,
    fuente,
    refresh = false,
  }: BuscarIncidenteParams): Promise<IncidenteBusquedaResponse> {
    const incNormalizado = inc.trim().toUpperCase();
    const res = await api.get<IncidenteBusquedaResponse>(`${BASE_URL}/buscar/`, {
      params: {
        inc: incNormalizado,
        ...(fuente ? { fuente } : {}),
        ...(refresh ? { refresh: true } : {}),
      },
      // Lecturas en frío de tablas grandes en Graph API pueden superar los 10s por defecto
      timeout: 45000,
    });
    return res.data;
  },
};
