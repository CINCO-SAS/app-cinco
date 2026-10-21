// src/modules/transporte/operacion/reporte-fotografico/reporteFotoView.tsx
//
// Vista de Reporte Fotográfico (F3/B3) — pestaña "Operación".
//
// Misma gramática que Salidas/Flota: barra de filtros + tabla. Aquí NO hay
// acciones de fila: el reporte se crea desde el modal y no se edita (el
// legacy tampoco lo permitía). Lo único que aporta esta vista por encima de
// la tabla es el AVISO de ventana de captura, porque la regla 10:00–16:00 es
// la que más reportes provoca y conviene verla sin abrir nada.
//
// Filtrado y paginación SERVER-SIDE: no se sabe cuántos reportes va a haber
// (uno por vehículo × técnico × día), así que pagina el servidor.

"use client";

import { useCallback, useMemo, useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useReporteFotoData } from "./reporteFotoView.hooks";
import { getReportesFotoColumns } from "./reporteFotoView.utils";
import { ReporteFotoTable } from "./components/ReporteFotoTable";
import { ReporteFotoToolbar } from "./components/ReporteFotoToolbar";
import { ReporteFotoFormModal } from "./components/ReporteFotoFormModal";

/** Aviso reutilizable de la ventana de captura (solo lectura de UI). */
const AvisoVentana = () => {
  const hora = new Date().getHours();
  const enVentana = hora >= 10 && hora <= 16;
  if (enVentana) return null;
  return (
    <Alert
      variant="warning"
      title="Fuera de la ventana de captura"
      message="La captura de reportes está permitida entre las 10:00 y las 16:00 (hora Colombia). Fuera de ese rango el servidor rechaza el alta."
    />
  );
};

const ReporteFotoView = () => {
  const {
    reportes,
    total,
    isLoading,
    loadError,
    recargar,
    filtros,
    actualizarFiltro,
    limpiarFiltros,
    hayFiltrosActivos,
    globalFilter,
    setGlobalFilter,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    setVisibleRows,
  } = useReporteFotoData();

  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const cerrarFormulario = useCallback(() => setFormularioAbierto(false), []);

  const columns = useMemo(() => getReportesFotoColumns(), []);

  // El DataTable solo sabe de `pageCount`: el total REAL lo tiene el
  // servidor (`count`) y de ahí sale cuántas páginas hay.
  const pageCount = useMemo(
    () => Math.max(Math.ceil(total / pageSize), 1),
    [total, pageSize],
  );

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb
        pageTitle={["Transporte", "Operación", "Reporte Fotográfico"]}
      />

      {loadError && (
        <div className="mb-4">
          <Alert
            variant="error"
            title="Error al cargar los reportes"
            message={loadError}
          />
        </div>
      )}

      <div className="mb-4">
        <AvisoVentana />
      </div>

      <ReporteFotoTable
        reportes={reportes}
        columns={columns}
        isLoading={isLoading}
        pageCount={pageCount}
        pageIndex={pageIndex}
        setPageIndex={setPageIndex}
        pageSize={pageSize}
        setPageSize={setPageSize}
        setVisibleRows={setVisibleRows}
        toolbarActions={
          <ReporteFotoToolbar
            total={total}
            filtros={filtros}
            actualizarFiltro={actualizarFiltro}
            limpiarFiltros={limpiarFiltros}
            hayFiltrosActivos={hayFiltrosActivos}
            busqueda={globalFilter}
            setBusqueda={setGlobalFilter}
            onNuevo={() => setFormularioAbierto(true)}
          />
        }
      />

      <ReporteFotoFormModal
        isOpen={formularioAbierto}
        onClose={cerrarFormulario}
        onGuardado={recargar}
      />
    </div>
  );
};

export default ReporteFotoView;
