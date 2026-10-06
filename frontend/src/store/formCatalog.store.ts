import { create } from "zustand";

/**
 * Estado global del "Catálogo Frecuente (Autocompletar 1-clic)" de los
 * formularios CAPEX.
 *
 * Cada chip del catálogo tiene un estado **por tarjeta** (SUMINISTRO #1,
 * ACTIVIDAD #1, ...):
 *
 *  - "pending":   sin usar todavía  → vive en el dropdown "Pendientes".
 *  - "used":      ya se aplicó a la tarjeta pero aún no se consolida → sigue
 *                 en el dropdown "Pendientes", marcado como "En uso".
 *  - "completed": consolidado al guardar o al navegar de paso → pasa al
 *                 dropdown "Completados".
 *
 * La agrupación entre dropdowns se deriva de este estado: los componentes solo
 * leen `statusesByCard[cardId]` y filtran el catálogo en consecuencia.
 */

export type CatalogChipStatus = "pending" | "used" | "completed";

/** Mínimo que debe tener un chip del catálogo para poder identificarlo. */
export interface CatalogChipLike {
  codigo_sap: string;
  texto_sap: string;
}

/** Identificador estable de un chip dentro de una tarjeta. */
export const catalogChipKey = (item: CatalogChipLike): string =>
  `${item.codigo_sap}::${item.texto_sap}`;

type CardChipStatuses = Record<string, CatalogChipStatus>;

export interface ConsolidateOptions {
  /** false cuando el formulario todavía tiene pasos incompletos. */
  formComplete?: boolean;
  /** Títulos de los pasos pendientes, para armar el aviso. */
  pendingStepTitles?: string[];
}

interface FormCatalogState {
  /** cardId → chipKey → status */
  statusesByCard: Record<string, CardChipStatuses>;
  /** Aviso mostrado al consolidar un formulario incompleto. */
  completionWarning: string | null;

  getStatus: (cardId: string, chipKey: string) => CatalogChipStatus;
  /** Marca un chip como "en uso" (se dispara al aplicarlo a la tarjeta). */
  markUsed: (cardId: string, chipKey: string) => void;
  /** Vuelve un chip a "pendiente" (deshacer). */
  resetChip: (cardId: string, chipKey: string) => void;
  /** Mueve todos los chips "used" a "completed" (guardar / navegar). */
  consolidate: (options?: ConsolidateOptions) => number;
  dismissCompletionWarning: () => void;
  /** Limpia todo el estado (al desmontar el formulario). */
  resetCatalog: () => void;
}

const buildWarning = (pendingStepTitles: string[] = []): string => {
  if (pendingStepTitles.length === 0) {
    return "Completa todos los pasos del formulario antes de guardar.";
  }

  return `Pasos pendientes: ${pendingStepTitles.join(", ")}.`;
};

export const useFormCatalogStore = create<FormCatalogState>((set, get) => ({
  statusesByCard: {},
  completionWarning: null,

  getStatus: (cardId, chipKey) =>
    get().statusesByCard[cardId]?.[chipKey] ?? "pending",

  markUsed: (cardId, chipKey) =>
    set((state) => {
      const current = state.statusesByCard[cardId]?.[chipKey] ?? "pending";
      if (current === "used") return {};

      return {
        statusesByCard: {
          ...state.statusesByCard,
          [cardId]: {
            ...(state.statusesByCard[cardId] ?? {}),
            [chipKey]: "used",
          },
        },
      };
    }),

  resetChip: (cardId, chipKey) =>
    set((state) => {
      const cardStatuses = state.statusesByCard[cardId];
      if (!cardStatuses || !(chipKey in cardStatuses)) return {};

      const rest = Object.fromEntries(
        Object.entries(cardStatuses).filter(([key]) => key !== chipKey),
      );

      return {
        statusesByCard: {
          ...state.statusesByCard,
          [cardId]: rest,
        },
      };
    }),

  consolidate: ({ formComplete = true, pendingStepTitles = [] } = {}) => {
    const state = get();
    let consolidated = 0;
    const nextStatuses: Record<string, CardChipStatuses> = {};

    for (const [cardId, cardStatuses] of Object.entries(state.statusesByCard)) {
      const nextCardStatuses: CardChipStatuses = {};

      for (const [chipKey, status] of Object.entries(cardStatuses)) {
        if (status === "used") {
          nextCardStatuses[chipKey] = "completed";
          consolidated += 1;
        } else {
          nextCardStatuses[chipKey] = status;
        }
      }

      nextStatuses[cardId] = nextCardStatuses;
    }

    set({
      statusesByCard: consolidated > 0 ? nextStatuses : state.statusesByCard,
      completionWarning: formComplete ? null : buildWarning(pendingStepTitles),
    });

    return consolidated;
  },

  dismissCompletionWarning: () => set({ completionWarning: null }),

  resetCatalog: () => set({ statusesByCard: {}, completionWarning: null }),
}));
