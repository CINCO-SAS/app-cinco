// ─── Agrupación visual del primer selector (UI) ───────────────────────────────
export type GrupoActividad =
  | "preventivos"
  | "correctivos_capex"
  | "emergencia_correctivos"; // engloba 'correctivos' y 'emergencias' de la BD

// ─── Valores exactos que se guardan en BD (campo `categoria`) ─────────────────
export type CategoriaActividad =
  | "preventivos"
  | "correctivos"
  | "emergencias"
  | "correctivos_capex";

// ─── Valores exactos que se guardan en BD (campo `tipo_formulario`) ───────────
export type TipoFormulario =
  // Preventivos
  | "aire_acondicionado"
  | "planta"
  // CAPEX
  | "tipologia1"
  | "tipologia3"
  | "tipologia5"
  // Emergencias / Correctivos
  | "estandar";

// ─── Estado unificado del formulario SMU ──────────────────────────────────────
export interface SmuFormState {
  /** Selección del primer radio (agrupación UI) */
  grupo: GrupoActividad | null;
  /** Valor real que va al campo `categoria` de la BD */
  categoria: CategoriaActividad | null;
  /** Valor real que va al campo `tipo_formulario` de la BD */
  tipo_formulario: TipoFormulario | null;
}
