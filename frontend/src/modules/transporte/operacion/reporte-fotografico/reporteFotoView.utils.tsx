// src/modules/transporte/operacion/reporte-fotografico/reporteFotoView.utils.tsx
//
// Columnas y formato de la tabla de Reportes Fotográficos (F3/B3).
//
// Todo sale de `ReporteFotograficoSerializer`: el backoffice piensa en PLACAS
// y en el NOMBRE del responsable, no en PKs.

import { ColumnDef } from "@tanstack/react-table";

import type { ReporteFotografico } from "@/types/transporte.types";

// ---------------------------------------------------------------------------
// Fechas
// ---------------------------------------------------------------------------

/** `YYYY-MM-DD` de hoy en zona del navegador (sin desfase de `new Date()`). */
export const hoyISO = (): string => {
  const ahora = new Date();
  const offset = ahora.getTimezoneOffset() * 60_000;
  return new Date(ahora.getTime() - offset).toISOString().slice(0, 10);
};

/**
 * `YYYY-MM-DD` desplazado n días. Se calcula en UTC para que el cambio de
 * huso horario no reste/gane un día por sorpresa.
 */
export const desplazarDias = (iso: string, dias: number): string => {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return fecha.toISOString().slice(0, 10);
};

/**
 * Rangos rápidos del toolbar. `dias` cuenta HOY dentro del intervalo, así
 * que "7 días" es hoy − 6.
 */
export const RANGOS_RAPIDOS = [
  { id: "hoy", etiqueta: "Hoy", dias: 0 },
  { id: "7", etiqueta: "7 días", dias: 6 },
  { id: "30", etiqueta: "30 días", dias: 29 },
] as const;

/** `YYYY-MM-DD` → `dd/mm/aaaa`; evita el desfase de `new Date()`. */
export const formatearFechaCorta = (valor?: string | null): string => {
  if (!valor) return "—";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
};

/** `10:22:31` → `10:22` (el informe se lee por hora, no por segundo). */
export const formatearHora = (valor?: string | null): string => {
  if (!valor) return "—";
  return valor.slice(0, 5);
};

/**
 * La ventana de captura es 10:00–16:00 (hora Colombia). Pintarla ayuda a
 * leer de un vistazo si el reporte salió en horario; el servidor es quien
 * realmente la exige (`en_ventana`), esto es solo lectura.
 */
export const FUERA_DE_VENTANA = { min: 10, max: 16 };

const estaEnVentana = (hora: string): boolean => {
  const hh = Number(hora.slice(0, 2));
  if (Number.isNaN(hh)) return true;
  return hh >= FUERA_DE_VENTANA.min && hh <= FUERA_DE_VENTANA.max;
};

/** `OT / actividad` del reporte; vacío → '—'. */
const otDe = (reporte: ReporteFotografico): string =>
  (reporte.ot_actividad ?? "").trim() || "—";

export const getReportesFotoColumns = (): ColumnDef<
  ReporteFotografico,
  unknown
>[] => [
  {
    id: "fecha",
    accessorKey: "fecha",
    header: "FECHA",
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
        {formatearFechaCorta(row.original.fecha)}
      </span>
    ),
  },
  {
    id: "hora",
    accessorKey: "hora",
    header: "HORA",
    cell: ({ row }) => {
      const hora = row.original.hora;
      const enVentana = estaEnVentana(hora);
      return (
        <span
          title={
            enVentana
              ? "Dentro de la ventana de captura (10:00–16:00)"
              : "Fuera de la ventana de captura (10:00–16:00)"
          }
          className={`whitespace-nowrap text-sm tabular-nums ${
            enVentana
              ? "text-gray-600 dark:text-gray-400"
              : "text-error-500"
          }`}
        >
          {formatearHora(hora)}
        </span>
      );
    },
  },
  {
    id: "placa",
    accessorKey: "placa",
    header: "PLACA",
    cell: ({ row }) => (
      <span className="font-medium text-gray-800 dark:text-white/90">
        {row.original.placa}
      </span>
    ),
  },
  {
    // El responsable NO lo elige el cliente: se deriva del usuario
    // autenticado (D-A10). Por eso no es editable ni filtrable a mano.
    id: "responsable",
    header: "RESPONSABLE",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {row.original.responsable_nombre || "—"}
        </span>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          CC {row.original.responsable_cedula}
        </span>
      </div>
    ),
  },
  {
    id: "ot_actividad",
    accessorKey: "ot_actividad",
    header: "OT / ACTIVIDAD",
    cell: ({ row }) => (
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {otDe(row.original)}
      </span>
    ),
  },
  {
    id: "evidencias",
    header: "EVIDENCIAS",
    enableSorting: false,
    cell: ({ row }) => {
      const imagenes = row.original.imagenes ?? [];
      if (imagenes.length === 0) {
        return <span className="text-gray-400">—</span>;
      }
      // Hasta 3 miniaturas + contador: suficiente para ver que HAY evidencia
      // sin convertir la fila en una galería.
      return (
        <div className="flex items-center gap-1.5">
          {imagenes.slice(0, 3).map((imagen, i) => (
            <a
              key={imagen.id}
              href={imagen.imagen}
              target="_blank"
              rel="noreferrer"
              title={imagen.nombre_original || `Imagen ${i + 1}`}
              className="block h-8 w-8 shrink-0 overflow-hidden rounded border border-gray-200 dark:border-gray-700"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imagen.imagen}
                alt={imagen.nombre_original || `Evidencia ${i + 1}`}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </a>
          ))}
          {imagenes.length > 3 && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              +{imagenes.length - 3}
            </span>
          )}
        </div>
      );
    },
  },
  {
    id: "observaciones",
    accessorKey: "observaciones",
    header: "OBSERVACIONES",
    cell: ({ row }) => {
      const texto = (row.original.observaciones ?? "").trim();
      if (!texto) return <span className="text-gray-400">—</span>;
      return (
        // Se corta en 2 líneas: la fila no debe crecer con un párrafo.
        <span
          title={texto}
          className="line-clamp-2 max-w-md text-sm text-gray-600 dark:text-gray-400"
        >
          {texto}
        </span>
      );
    },
  },
];
