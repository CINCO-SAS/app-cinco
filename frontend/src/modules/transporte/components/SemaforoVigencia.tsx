// src/modules/transporte/components/SemaforoVigencia.tsx
//
// Badge del semáforo documental (SOAT / CDA / licencia del conductor).
//
// El ESTADO lo calcula EN SERVIDOR (`services/vigencia.py`): aquí solo se
// traduce a color. Regla de negocio (§5.3):
//   >60 días  → VIGENTE    (verde)
//   31–60 días → POR_VENCER (naranja)
//   ≤30 o vencida → VENCIDA (rojo)
//   sin fecha  → SIN_REGISTRO (gris)

import Badge from "@/components/ui/badge/Badge";
import type { EstadoVigencia } from "@/types/transporte.types";

/** Mapeo estado → color del Badge. Fuente única de verdad del semáforo. */
const COLOR_POR_ESTADO: Record<
  EstadoVigencia,
  "success" | "warning" | "error" | "light"
> = {
  VIGENTE: "success",
  POR_VENCER: "warning",
  VENCIDA: "error",
  SIN_REGISTRO: "light",
};

/** Etiqueta legible para el usuario. */
const ETIQUETA_POR_ESTADO: Record<EstadoVigencia, string> = {
  VIGENTE: "Vigente",
  POR_VENCER: "Por vencer",
  VENCIDA: "Vencida",
  SIN_REGISTRO: "Sin registro",
};

interface SemaforoVigenciaProps {
  estado: EstadoVigencia;
  /** Muestra la fecha debajo del badge (opcional, para las fichas). */
  fecha?: string | null;
  size?: "sm" | "md";
}

/**
 * Punto de color sin texto — para las tablas densas donde el tooltip
 * aporta la fecha y el texto solo ensucia.
 */
export const PuntoVigencia = ({ estado }: { estado: EstadoVigencia }) => {
  const clase = {
    VIGENTE: "bg-success-500",
    POR_VENCER: "bg-warning-500",
    VENCIDA: "bg-error-500",
    SIN_REGISTRO: "bg-gray-300 dark:bg-white/20",
  }[estado];

  return (
    <span
      title={ETIQUETA_POR_ESTADO[estado]}
      className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${clase}`}
    />
  );
};

const SemaforoVigencia: React.FC<SemaforoVigenciaProps> = ({
  estado,
  fecha,
  size = "md",
}) => (
  <div className="flex flex-col gap-0.5">
    <Badge color={COLOR_POR_ESTADO[estado]} size={size} variant="light">
      {ETIQUETA_POR_ESTADO[estado]}
    </Badge>
    {fecha && (
      <span className="text-xs text-gray-400 dark:text-gray-500">
        {formatearFecha(fecha)}
      </span>
    )}
  </div>
);

/** `YYYY-MM-DD` → `dd/mm/yyyy` (evita el desfase de zona horaria de Date). */
const formatearFecha = (valor: string): string => {
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
};

export default SemaforoVigencia;
