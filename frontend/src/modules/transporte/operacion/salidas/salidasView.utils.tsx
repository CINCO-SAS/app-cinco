// src/modules/transporte/operacion/salidas/salidasView.utils.tsx
//
// Columnas, etiquetas y formato de la tabla de Salidas (B1).
//
// Fuente de datos: `SalidaSerializer`, que expone `vehiculo_placa`, el
// detalle de personas (`conductor_detalle` / `tecnico_asignado_detalle`),
// `valor_dia`, `valor_novedad`, `total_a_pagar` (B10) y `puede_gestionar`
// (B15) — todo calculado en servidor, el front solo pinta.

import { ColumnDef } from "@tanstack/react-table";

import Badge from "@/components/ui/badge/Badge";
import type {
  EstadoSalida,
  Salida,
} from "@/types/transporte.types";

export const SALIDAS_TABLE_CONFIG = {
  defaultPageSize: 25,
  defaultPageIndex: 0,
} as const;

/**
 * Estado → color del Badge. Sigue la máquina de estados del backend
 * (D-A11: REPORTADO → APROBADO/RECHAZADO/ELIMINADO; APROBADO → VALIDADO).
 */
const COLOR_ESTADO: Record<
  EstadoSalida,
  "warning" | "success" | "error" | "primary" | "light"
> = {
  REPORTADO: "warning",
  APROBADO: "success",
  RECHAZADO: "error",
  VALIDADO: "primary",
  ELIMINADO: "light",
};

const ETIQUETA_ESTADO: Record<EstadoSalida, string> = {
  REPORTADO: "Reportado",
  APROBADO: "Aprobado",
  RECHAZADO: "Rechazado",
  VALIDADO: "Validado",
  ELIMINADO: "Eliminado",
};

/** Reutilizado por el `<select>` de estado del toolbar. */
export const ETIQUETAS_ESTADO = ETIQUETA_ESTADO;

export const BadgeEstadoSalida = ({ estado }: { estado: EstadoSalida }) => (
  <Badge color={COLOR_ESTADO[estado]} size="sm">
    {ETIQUETA_ESTADO[estado] ?? estado}
  </Badge>
);

/**
 * Botón destructivo. `Button` de la design system solo trae `primary` y
 * `outline` (rojo en el rojo del tema base no aplica), así que aquí va un
 * `<button>` plano con los tokens `error-*` que sí usan el resto de
 * pantallas para borrar/inactivar.
 */
export const BotonDestructivo = ({
  children,
  onClick,
  disabled,
  size = "sm",
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  size?: "sm" | "md";
}) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    className={`inline-flex items-center justify-center rounded-lg font-medium text-error-500 ring-1 ring-inset ring-error-500 transition hover:bg-error-500 hover:text-white disabled:cursor-not-allowed disabled:opacity-50 ${
      size === "sm" ? "px-2 py-1.5 text-sm" : "px-4 py-2.5 text-sm"
    }`}
  >
    {children}
  </button>
);

// ---------------------------------------------------------------------------
// Formato
// ---------------------------------------------------------------------------

/** `YYYY-MM-DD` → `dd/mm`; evita el desfase horario de `new Date()`. */
export const formatearFechaCorta = (valor?: string | null): string => {
  if (!valor) return "—";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
};

/** `1234567.89` → `$ 1.234.568`. */
export const formatearMoneda = (valor?: string | number | null): string => {
  if (valor === null || valor === undefined || valor === "") return "$ 0";
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return "$ 0";
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(numero);
};

/** Fecha ISO de hoy en zona del navegador, formato `YYYY-MM-DD`. */
export const hoyISO = (): string => {
  const ahora = new Date();
  const offset = ahora.getTimezoneOffset() * 60_000;
  return new Date(ahora.getTime() - offset).toISOString().slice(0, 10);
};

/**
 * `YYYY-MM-DD` desplazado n días. Se calcula en UTC para que el cambio de
 * huso horario (o el cálculo del offset) no reste/gane un día por sorpresa.
 */
export const desplazarDias = (iso: string, dias: number): string => {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return fecha.toISOString().slice(0, 10);
};

/**
 * Rangos rápidos de B1. `dias` es el ancho del intervalo contando HOY.
 * El backend recibe `desde`/`hasta` en ISO; el front solo arma el rango.
 */
export const RANGOS_RAPIDOS = [
  { id: "hoy", etiqueta: "Hoy", dias: 0 },
  { id: "7", etiqueta: "7 días", dias: 6 },
  { id: "30", etiqueta: "30 días", dias: 29 },
] as const;

// ---------------------------------------------------------------------------
// Columnas
// ---------------------------------------------------------------------------

/**
 * Nombre en 1ª línea y cédula en 2ª. Reutilizado por las dos columnas de
 * personas: `conductor_detalle` (quien sale) y `tecnico_asignado_detalle`
 * (móvil de nómina) llegan con la MISMA forma desde el backend.
 */
const Persona = ({ nombre, cedula }: { nombre: string; cedula: string }) => (
  <div className="flex flex-col">
    <span className="text-sm text-gray-700 dark:text-gray-300">
      {nombre || "—"}
    </span>
    <span className="text-xs text-gray-400 dark:text-gray-500">
      CC {cedula}
    </span>
  </div>
);

const MONEDA_CLASE =
  "whitespace-nowrap text-sm tabular-nums text-gray-700 dark:text-gray-300";

// ---------------------------------------------------------------------------
// Ítem L · selección y acciones de fila
// ---------------------------------------------------------------------------

/** Lo que las columnas necesitan saber del hook de acciones (B5–B15). */
export interface AccionesFila {
  seleccion: Set<number>;
  alternarFila: (id: number) => void;
  alternarPagina: (ids: number[], marcar: boolean) => void;
  abrirConfirmar: (
    accion: "aprobar" | "eliminar" | "validar",
    salida: Salida,
  ) => void;
  abrirRechazar: (salida: Salida) => void;
  abrirNovedad: (salida: Salida) => void;
  abrirHistorial: (salida: Salida) => void;
}

/**
 * Enlace-texto de la columna de acciones. Se eligió texto plano y no un
 * `<Button>` para que la tabla no se ensanche: con hasta 4 acciones por fila,
 * botones con fondo harían ilegible una tabla de 11 columnas.
 */
const BotonFila = ({
  children,
  onClick,
  tono = "normal",
}: {
  children: React.ReactNode;
  onClick: () => void;
  tono?: "normal" | "peligro";
}) => (
  <button
    type="button"
    onClick={onClick}
    className={`whitespace-nowrap text-xs font-medium underline-offset-2 transition hover:underline ${
      tono === "peligro"
        ? "text-error-500 hover:text-error-600"
        : "text-brand-500 hover:text-brand-600"
    }`}
  >
    {children}
  </button>
);

export const getSalidasColumns = (
  acciones: AccionesFila,
): ColumnDef<Salida, unknown>[] => [
  // --- Selección (B12) --------------------------------------------------
  {
    id: "seleccion",
    enableSorting: false,
    size: 36,
    header: ({ table }) => {
      // SOLO las filas de la página actual: con `manualPagination` el
      // servidor devuelve una porción, así que "seleccionar todo" no puede
      // prometer el total del filtro.
      const filas = table.getRowModel().rows.map((fila) => fila.original);
      const gestionables = filas.filter((f) => f.puede_gestionar);
      const todos = gestionables.length > 0 && gestionables.every(
        (f) => acciones.seleccion.has(f.id),
      );
      return (
        <input
          type="checkbox"
          aria-label="Seleccionar todas las filas de la página"
          checked={todos}
          disabled={gestionables.length === 0}
          onChange={(e) =>
            acciones.alternarPagina(
              gestionables.map((f) => f.id),
              e.target.checked,
            )
          }
          className="h-4 w-4 cursor-pointer rounded border-gray-300 text-brand-500 focus:ring-brand-500/20 dark:border-gray-700"
        />
      );
    },
    cell: ({ row }) => (
      // B15: solo el servidor sabe quién gestiona; el front no habilita
      // casillas que luego el backend rechazaría con 403.
      <input
        type="checkbox"
        aria-label={`Seleccionar salida ${row.original.vehiculo_placa}`}
        checked={acciones.seleccion.has(row.original.id)}
        disabled={!row.original.puede_gestionar}
        onChange={() => acciones.alternarFila(row.original.id)}
        className="h-4 w-4 cursor-pointer rounded border-gray-300 text-brand-500 focus:ring-brand-500/20 dark:border-gray-700"
      />
    ),
  },
  {
    id: "fecha_salida",
    accessorKey: "fecha_salida",
    header: "FECHA",
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
        {formatearFechaCorta(row.original.fecha_salida)}
      </span>
    ),
  },
  {
    id: "vehiculo_placa",
    accessorKey: "vehiculo_placa",
    header: "PLACA",
    cell: ({ row }) => (
      <span className="font-medium text-gray-800 dark:text-white/90">
        {row.original.vehiculo_placa}
      </span>
    ),
  },
  {
    // Legacy `movil_sale`: la persona que SALE (o la sentinella 'disponible',
    // que aquí ya es un flag y no texto).
    id: "quien_sale",
    header: "QUIÉN SALE",
    enableSorting: false,
    cell: ({ row }) => {
      const { conductor_detalle, es_disponible } = row.original;
      if (es_disponible) {
        return (
          <Badge color="light" size="sm">
            Disponible
          </Badge>
        );
      }
      if (!conductor_detalle) return <span className="text-gray-400">—</span>;
      return (
        <Persona
          nombre={conductor_detalle.nombre}
          cedula={conductor_detalle.cedula}
        />
      );
    },
  },
  {
    // Legacy `cc_asignada` / `cedula_tecnico`: personal de nómina asignado.
    id: "movil_asignada",
    header: "MÓVIL ASIGNADA",
    enableSorting: false,
    cell: ({ row }) => {
      const detalle = row.original.tecnico_asignado_detalle;
      if (!detalle) return <span className="text-gray-400">—</span>;
      return <Persona nombre={detalle.nombre} cedula={detalle.cedula} />;
    },
  },
  {
    id: "area",
    accessorKey: "area",
    header: "ÁREA",
    cell: ({ row }) => (
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {row.original.area || "—"}
      </span>
    ),
  },
  // --- B10: valor día · valor novedad · total ---------------------------
  {
    id: "valor_dia",
    accessorKey: "valor_dia",
    header: "VALOR DÍA",
    cell: ({ row }) => (
      <span className={MONEDA_CLASE}>{formatearMoneda(row.original.valor_dia)}</span>
    ),
  },
  {
    id: "valor_novedad",
    accessorKey: "valor_novedad",
    header: "NOVEDAD",
    cell: ({ row }) => {
      const valor = row.original.valor_novedad;
      if (Number(valor) === 0) return <span className="text-gray-400">—</span>;
      return <span className={`${MONEDA_CLASE} text-amber-600 dark:text-amber-400/90`}>{formatearMoneda(valor)}</span>;
    },
  },
  {
    id: "total_a_pagar",
    accessorKey: "total_a_pagar",
    header: "TOTAL",
    cell: ({ row }) => (
      <span className={`${MONEDA_CLASE} font-medium text-gray-800 dark:text-white/90`}>
        {formatearMoneda(row.original.total_a_pagar)}
      </span>
    ),
  },
  {
    id: "estado",
    accessorKey: "estado",
    header: "ESTADO",
    cell: ({ row }) => <BadgeEstadoSalida estado={row.original.estado} />,
  },
  // B14: Badge Reporte SI/NO.
  {
    id: "reportado",
    accessorKey: "reportado",
    header: "REPORTE",
    cell: ({ row }) =>
      row.original.reportado ? (
        <Badge color="success" size="sm">
          Sí
        </Badge>
      ) : (
        <Badge color="light" size="sm">
          No
        </Badge>
      ),
  },
  // --- Ítem L · acciones (B5/B6/B7/B13) ---------------------------------
  {
    id: "acciones",
    enableSorting: false,
    size: 200,
    header: () => <span className="sr-only">Acciones</span>,
    cell: ({ row }) => {
      const salida = row.original;
      const gestiona = salida.puede_gestionar;
      return (
        <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1">
          {gestiona && salida.estado === "REPORTADO" && (
            <>
              <BotonFila onClick={() => acciones.abrirConfirmar("aprobar", salida)}>
                Aprobar
              </BotonFila>
              <BotonFila tono="peligro" onClick={() => acciones.abrirRechazar(salida)}>
                Rechazar
              </BotonFila>
              <BotonFila tono="peligro" onClick={() => acciones.abrirConfirmar("eliminar", salida)}>
                Eliminar
              </BotonFila>
            </>
          )}

          {gestiona && salida.estado === "APROBADO" && (
            <BotonFila onClick={() => acciones.abrirConfirmar("validar", salida)}>
              Validar
            </BotonFila>
          )}

          {/* Novedad solo en estados vivos: sobre VALIDADO ya se liquidó. */}
          {gestiona &&
            (salida.estado === "REPORTADO" || salida.estado === "APROBADO") && (
              <BotonFila onClick={() => acciones.abrirNovedad(salida)}>
                {salida.novedad_detalle ? "Ver novedad" : "Novedad"}
              </BotonFila>
            )}

          {/* Historial: es trazabilidad, todos pueden verlo. */}
          <BotonFila onClick={() => acciones.abrirHistorial(salida)}>
            Historial
          </BotonFila>
        </div>
      );
    },
  },
];
