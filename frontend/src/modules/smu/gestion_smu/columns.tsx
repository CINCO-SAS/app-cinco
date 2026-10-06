// src/modules/smu/gestion_smu/columns.tsx
//
// Columnas de la tabla de gestión SMU y las columnas espejo del export CSV.
// Comparten el mismo orden para que el archivo refleje lo que se ve en pantalla.

import { useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import { DownloadIcon } from "@/icons";
import {
  descargarExcelActividadSMU,
  tienePlantillaExporte,
  type ActividadSmuResumen,
} from "@/services/smu.service";
import type { CsvColumn } from "@/utils/csv";

type ColorEstado = "primary" | "success" | "warning" | "error";

const COLORES_ESTADO: Record<string, ColorEstado> = {
  borrador: "warning",
  enviado: "primary",
  aprobado: "success",
  rechazado: "error",
};

/** `2026-09-30T10:12:00-05:00` → `30/09/2026`; vacío o inválido → `-`. */
const formatoFecha = (valor?: string | null): string => {
  if (!valor) return "-";
  const fecha = new Date(valor);
  if (!Number.isNaN(fecha.getTime())) return fecha.toLocaleDateString("es-CO");
  // DRF serializa fechas históricas con offsets que JS rechaza (p. ej.
  // `1212-12-12T00:12:00-04:56:16`); en vez de mostrar "-", rescatamos el
  // día calendario del propio texto ISO.
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(valor);
  if (!m) return "-";
  const rescatada = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(rescatada.getTime())) return "-";
  return rescatada.toLocaleDateString("es-CO");
};

/** `2026-09-30T10:12:00-05:00` → `30/09/2026 10:12`; vacío → `-`. */
const formatoFechaHora = (valor?: string | null): string => {
  if (!valor) return "-";
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return "-";
  return fecha.toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
};

const texto = (valor?: string | null): string => valor?.trim() || "-";

/**
 * Descarga el Excel del formulario con el estilo que le corresponde según su
 * tipo. Si ese tipo todavía no tiene plantilla, el botón queda deshabilitado
 * (el backend devolvería 400).
 */
const BotonExportarFormulario = ({
  actividad,
}: {
  actividad: ActividadSmuResumen;
}) => {
  const [cargando, setCargando] = useState(false);
  const disponible = tienePlantillaExporte(actividad);

  const exportar = async () => {
    setCargando(true);
    try {
      await descargarExcelActividadSMU(actividad);
    } catch (error) {
      toast.error(
        error instanceof Error && error.message
          ? error.message
          : "No se pudo generar el Excel de este formulario.",
      );
    } finally {
      setCargando(false);
    }
  };

  const ayuda = disponible
    ? "Descargar el formulario en Excel"
    : "Este tipo de formulario aún no tiene plantilla de exporte";

  return (
    <span title={ayuda}>
      <Button
        variant="outline"
        size="sm"
        className="flex items-center gap-1.5 whitespace-nowrap"
        onClick={exportar}
        disabled={cargando || !disponible}
        startIcon={<DownloadIcon className="h-4 w-4" />}
      >
        {cargando ? "Generando…" : "Excel"}
      </Button>
    </span>
  );
};

export const getGestionSmuColumns = (): ColumnDef<ActividadSmuResumen>[] => [
  {
    id: "codigo_ot",
    header: "OT",
    accessorKey: "codigo_ot",
    cell: ({ getValue }) => <span>{texto(getValue<string>())}</span>,
  },
  {
    id: "tipo_formulario_display",
    header: "TIPO FORMULARIO",
    accessorKey: "tipo_formulario_display",
    cell: ({ getValue }) => <span>{getValue<string>()}</span>,
  },
  {
    id: "tipo_estacion",
    header: "TIPO DE PLANTA",
    accessorKey: "tipo_estacion",
    cell: ({ getValue }) => <span>{texto(getValue<string>())}</span>,
  },
  {
    id: "nombre_estacion",
    header: "ESTACIÓN",
    accessorKey: "nombre_estacion",
    cell: ({ getValue }) => {
      const estacion = getValue<string>();
      return <span title={estacion}>{estacion}</span>;
    },
  },
  {
    id: "responsable_nombre",
    header: "RESPONSABLE",
    accessorKey: "responsable_nombre",
    cell: ({ getValue }) => <span>{texto(getValue<string>())}</span>,
  },
  {
    id: "responsable_cedula",
    header: "CÉDULA",
    accessorKey: "responsable_cedula",
    cell: ({ getValue }) => <span>{texto(getValue<string>())}</span>,
  },
  {
    id: "categoria_display",
    header: "CATEGORÍA",
    accessorKey: "categoria_display",
    cell: ({ getValue }) => <span>{getValue<string>()}</span>,
  },
  {
    id: "estado",
    header: "ESTADO",
    accessorKey: "estado",
    cell: ({ row }) => (
      <Badge size="sm" color={COLORES_ESTADO[row.original.estado] ?? "light"}>
        {row.original.estado_display}
      </Badge>
    ),
  },
  {
    id: "fecha_inicio",
    header: "INICIO",
    accessorKey: "fecha_inicio",
    cell: ({ getValue }) => <span>{formatoFecha(getValue<string>())}</span>,
  },
  {
    id: "created_at",
    header: "REGISTRADO",
    accessorKey: "created_at",
    cell: ({ getValue }) => (
      <span>{formatoFechaHora(getValue<string>())}</span>
    ),
  },
  {
    id: "acciones",
    header: "EXPORTAR",
    enableSorting: false,
    cell: ({ row }) => <BotonExportarFormulario actividad={row.original} />,
  },
];

export const gestionSmuCsvColumns: CsvColumn<ActividadSmuResumen>[] = [
  { header: "OT", accessor: (row) => row.codigo_ot ?? "" },
  { header: "Tipo formulario", accessor: (row) => row.tipo_formulario_display },
  { header: "Tipo de planta", accessor: (row) => row.tipo_estacion ?? "" },
  { header: "Estación", accessor: (row) => row.nombre_estacion },
  { header: "Responsable", accessor: (row) => row.responsable_nombre ?? "" },
  { header: "Cédula", accessor: (row) => row.responsable_cedula ?? "" },
  { header: "Categoría", accessor: (row) => row.categoria_display },
  { header: "Estado", accessor: (row) => row.estado_display },
  { header: "Inicio", accessor: (row) => formatoFecha(row.fecha_inicio) },
  {
    header: "Registrado",
    accessor: (row) => formatoFechaHora(row.created_at),
  },
];
