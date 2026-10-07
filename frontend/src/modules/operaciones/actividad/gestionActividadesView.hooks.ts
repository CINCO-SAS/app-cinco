import { useEffect, useMemo, useState } from "react";
import { useActividadStore } from "@/store/actividad.store";
import { useTableUrlState } from "@/hooks/useTableUrlState";
import { ColumnDef } from "@tanstack/react-table";
import { ActividadRecord } from "@/schemas/actividades.schema";
import { ACTIVIDAD_TABLE_CONFIG } from "./actividadTable.utils";
import { getActividadesColumns } from "./gestionActividadesView.utils";
import { logDevelopmentError } from "@/lib/environment";
import { ApiError } from "@/lib/errorHandler";

const formatLoadErrorForLog = (error: unknown) => {
  if (error instanceof Error) {
    const apiError = error as ApiError;

    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
      type: apiError.type,
      status: apiError.status,
      errors: apiError.errors,
      originalError: apiError.originalError,
    };
  }

  return error;
};

export const useGestionActividadesData = () => {
  const { loadActividades, actividades, loadError, loadWarning } =
    useActividadStore();
  const [showAlert, setShowAlert] = useState(false);
  const [visibleRows, setVisibleRows] = useState<ActividadRecord[]>([]);

  const {
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  } = useTableUrlState({
    defaultPageSize: ACTIVIDAD_TABLE_CONFIG.defaultPageSize,
    defaultPageIndex: ACTIVIDAD_TABLE_CONFIG.defaultPageIndex,
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        await loadActividades();
      } catch (error) {
        logDevelopmentError(
          "Error cargando actividades:",
          formatLoadErrorForLog(error),
        );
      }
    };

    void loadData();
  }, [loadActividades]);

  useEffect(() => {
    if (!showAlert) return;

    const timer = setTimeout(() => {
      setShowAlert(false);
    }, 5000);

    return () => clearTimeout(timer);
  }, [showAlert]);

  const [fechaDesde, setFechaDesde] = useState<string>(() => {
    const hoy = new Date();
    const primerDia = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    const y = primerDia.getFullYear();
    const m = String(primerDia.getMonth() + 1).padStart(2, "0");
    const d = String(primerDia.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  });

  const [fechaHasta, setFechaHasta] = useState<string>(() => {
    const hoy = new Date();
    const ultimoDia = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0);
    const y = ultimoDia.getFullYear();
    const m = String(ultimoDia.getMonth() + 1).padStart(2, "0");
    const d = String(ultimoDia.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  });

  const handleFechaDesdeChange = (fecha: string) => {
    setFechaDesde(fecha);
    setPageIndex(0);
  };

  const handleFechaHastaChange = (fecha: string) => {
    setFechaHasta(fecha);
    setPageIndex(0);
  };

  const handleLimpiarFiltroFecha = () => {
    setFechaDesde("");
    setFechaHasta("");
    setPageIndex(0);
  };

  // Filtrar actividades por rango de fechas
  const actividadesFiltradas = useMemo(() => {
    if (!fechaDesde && !fechaHasta) {
      return actividades;
    }

    return actividades.filter((act: ActividadRecord) => {
      const fIni = act.fecha_inicio ? act.fecha_inicio.substring(0, 10) : "";
      const fFin = act.fecha_fin_estimado ? act.fecha_fin_estimado.substring(0, 10) : fIni;
      const fItem = fIni || fFin;

      if (!fItem) return false;

      if (fechaDesde && fechaHasta) {
        return (
          (fIni >= fechaDesde && fIni <= fechaHasta) ||
          (fFin >= fechaDesde && fFin <= fechaHasta) ||
          (fIni <= fechaDesde && fFin >= fechaHasta)
        );
      }

      if (fechaDesde) {
        return (fFin || fIni) >= fechaDesde;
      }

      if (fechaHasta) {
        return (fIni || fFin) <= fechaHasta;
      }

      return true;
    });
  }, [actividades, fechaDesde, fechaHasta]);

  const columns: ColumnDef<ActividadRecord>[] = useMemo(
    () => getActividadesColumns(),
    [],
  );

  return {
    actividades: actividadesFiltradas,
    totalActividades: actividades.length,
    actividadesFiltradasCount: actividadesFiltradas.length,
    fechaDesde,
    fechaHasta,
    setFechaDesde: handleFechaDesdeChange,
    setFechaHasta: handleFechaHastaChange,
    handleLimpiarFiltroFecha,
    columns,
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    visibleRows,
    setVisibleRows,
    showAlert,
    setShowAlert,
    loadError,
    loadWarning,
  };
};
