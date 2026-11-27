export interface IncidenteFuente {
  key: string;
  label: string;
  habilitado: boolean;
}

export interface IncidenteRegistro {
  inc: string;
  f_creacion: string | null;
  ot: string;
  cliente: string;
  estado: string;
}

export interface IncidenteBusquedaResponse {
  success: boolean;
  encontrado: boolean;
  fuente: {
    key: string;
    label: string;
  };
  inc: string;
  principal: IncidenteRegistro | null;
  coincidencias: IncidenteRegistro[];
  total_coincidencias: number;
  stale: boolean;
  refreshed: boolean;
  cooldown_active: boolean;
  cached_at: string | null;
  antiguedad_minutos: number;
  cooldown_segundos: number;
  detail?: string;
}
