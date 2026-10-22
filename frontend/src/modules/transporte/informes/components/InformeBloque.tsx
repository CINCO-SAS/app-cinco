// src/modules/transporte/informes/components/InformeBloque.tsx
//
// Tarjeta de un bloque de informe: encabezado con el rótulo y el período,
// y dentro la tabla de áreas (`InformeTablaAreas`).
//
// Es el MISMO componente para "Transporte Día" y "Transporte Mes" porque
// los dos pintan `AreaInforme[]`. La única diferencia de comportamiento —
// el interruptor "Solo aprobados"— ya viene resuelta en los datos, así que
// aquí solo se refleja como nota.

import Alert from "@/components/ui/alert/Alert";

import type { AreaInforme } from "@/types/transporte.types";
import { InformeTablaAreas } from "./InformeTablaAreas";

interface InformeBloqueProps {
  titulo: string;
  /** Rótulo del período visible, p. ej. `05/10/2026` u `OCTUBRE 2026`. */
  periodo: string;
  areas: AreaInforme[];
  isLoading?: boolean;
  error?: string | null;
  /** Nota bajo el encabezado (se omite si es `undefined`). */
  nota?: string;
}

export const InformeBloque = ({
  titulo,
  periodo,
  areas,
  isLoading = false,
  error = null,
  nota,
}: InformeBloqueProps) => (
  <section className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
    <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 px-4 py-3 dark:border-white/5">
      <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">
        {titulo}
      </h3>
      <span className="text-sm font-medium text-brand-500 dark:text-brand-400">
        {periodo}
      </span>
    </header>

    {nota && (
      <p className="border-b border-gray-100 bg-gray-50 px-4 py-2 text-xs leading-relaxed text-gray-500 dark:border-white/5 dark:bg-gray-800/40 dark:text-gray-400">
        {nota}
      </p>
    )}

    <div className="p-2">
      {error ? (
        <div className="p-2">
          <Alert
            variant="error"
            title={`No se pudo cargar «${titulo}»`}
            message={error}
          />
        </div>
      ) : (
        <InformeTablaAreas areas={areas} isLoading={isLoading} />
      )}
    </div>
  </section>
);
