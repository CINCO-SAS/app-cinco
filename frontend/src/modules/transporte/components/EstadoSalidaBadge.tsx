// src/modules/transporte/components/EstadoSalidaBadge.tsx
//
// Badge del estado de una salida, COMPARTIDO por las pantallas del módulo
// que pintan filas de `Salida` (Operación → Salidas y Administración →
// Informes, bloque "Día a Día").
//
// Antes vivía en `operacion/salidas/salidasView.utils.tsx`. Cuando el bloque
// Día a Día empezó a pintar las mismas filas, repetir el mapa de colores
// habría creado una SEGUNDA fuente de verdad para una sola máquina de
// estados (D-A11: REPORTADO → APROBADO/RECHAZADO/ELIMINADO;
// APROBADO → VALIDADO): cambiar un color obligaría a tocar dos archivos.
//
// Moverlo aquí fue el mismo criterio que `SemaforoVigencia`: si dos
// pantallas muestran lo mismo, el componente es del módulo, no de una
// pantalla.

import Badge from "@/components/ui/badge/Badge";

import type { EstadoSalida } from "@/types/transporte.types";

type TonoBadge = "warning" | "success" | "error" | "primary" | "light";

/** Estado → color del Badge (sigue la máquina de estados del backend). */
export const COLOR_ESTADO: Record<EstadoSalida, TonoBadge> = {
  REPORTADO: "warning",
  APROBADO: "success",
  RECHAZADO: "error",
  VALIDADO: "primary",
  ELIMINADO: "light",
};

export const ETIQUETA_ESTADO: Record<EstadoSalida, string> = {
  REPORTADO: "Reportado",
  APROBADO: "Aprobado",
  RECHAZADO: "Rechazado",
  VALIDADO: "Validado",
  ELIMINADO: "Eliminado",
};

/** Etiquetas para los `<select>` de estado (vacío = todas). */
export const ETIQUETAS_ESTADO = ETIQUETA_ESTADO;

export const BadgeEstadoSalida = ({ estado }: { estado: EstadoSalida }) => (
  <Badge color={COLOR_ESTADO[estado]} size="sm">
    {ETIQUETA_ESTADO[estado] ?? estado}
  </Badge>
);
