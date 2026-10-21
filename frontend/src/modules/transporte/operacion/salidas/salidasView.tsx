// src/modules/transporte/operacion/salidas/salidasView.tsx
//
// Vista de Salidas — registro diario de salidas de móvil (B1) de la
// pestaña "Operación".
//
// Deliberadamente liviana (misma gramática que Flota/Conductores): una barra
// de filtros + tabla. Todo el volumen está en el servidor: aquí no hay KPIs
// ni párrafos, solo filas paginadas (`manualPagination`).
//
// Ítem L añade las acciones de fila (aprobar/rechazar/eliminar/novedad/
// historial) y la selección múltiple para aprobar en lote. Ese es el único
// punto donde esta vista ESCRIBE: todo lo demás es consulta.

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useSalidasData } from "./salidasView.hooks";
import { useSalidasAcciones } from "./salidasView.acciones";
import { getSalidasColumns } from "./salidasView.utils";
import { SalidasTable } from "./components/SalidasTable";
import { SalidasToolbar } from "./components/SalidasToolbar";
import { SalidaFormModal } from "./components/SalidaFormModal";
import {
  SalidaAprobarLoteModal,
  SalidaConfirmarModal,
  SalidaRechazarModal,
} from "./components/SalidaAccionModal";
import { SalidaNovedadModal } from "./components/SalidaNovedadModal";
import { SalidaHistorialModal } from "./components/SalidaHistorialModal";

const SalidasView = () => {
  const {
    salidas,
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
  } = useSalidasData();

  const acciones = useSalidasAcciones(recargar);

  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const cerrarFormulario = useCallback(() => setFormularioAbierto(false), []);

  // Cambiar de página cambia las filas en pantalla: la selección vieja quedaría
  // invisible pero activa y el usuario aprobaría filas que no ve.
  useEffect(() => {
    acciones.limpiarSeleccion();
  }, [pageIndex, pageSize, acciones.limpiarSeleccion]);

  const columns = useMemo(
    () => getSalidasColumns(acciones),
    [acciones],
  );

  // El DataTable solo sabe de `pageCount`: el total REAL lo tiene el
  // servidor (`count`) y de ahí sale cuántas páginas hay.
  const pageCount = useMemo(
    () => Math.max(Math.ceil(total / pageSize), 1),
    [total, pageSize],
  );

  /** B12: el diálogo de lote se cierra SOLO si el servidor aceptó. */
  const confirmarLote = useCallback(async (): Promise<boolean> => {
    const fallo = await acciones.aprobarLote();
    if (!fallo) acciones.cerrarDialogo();
    return fallo;
  }, [acciones]);

  const confirmarAccionSimple = useCallback(async () => {
    const fallo = await acciones.confirmarAccionSimple();
    if (!fallo) acciones.cerrarDialogo();
  }, [acciones]);

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb pageTitle={["Transporte", "Operación", "Salidas"]} />

      {loadError && (
        <div className="mb-4">
          <Alert
            variant="error"
            title="Error al cargar las salidas"
            message={loadError}
          />
        </div>
      )}

      <SalidasTable
        salidas={salidas}
        columns={columns}
        isLoading={isLoading}
        pageCount={pageCount}
        pageIndex={pageIndex}
        setPageIndex={setPageIndex}
        pageSize={pageSize}
        setPageSize={setPageSize}
        setVisibleRows={setVisibleRows}
        toolbarActions={
          <SalidasToolbar
            total={total}
            filtros={filtros}
            actualizarFiltro={actualizarFiltro}
            limpiarFiltros={limpiarFiltros}
            hayFiltrosActivos={hayFiltrosActivos}
            busqueda={globalFilter}
            setBusqueda={setGlobalFilter}
            onNuevo={() => setFormularioAbierto(true)}
            seleccionCantidad={acciones.seleccionCantidad}
            onAprobarLote={acciones.abrirLote}
            onLimpiarSeleccion={acciones.limpiarSeleccion}
          />
        }
      />

      <SalidaFormModal
        isOpen={formularioAbierto}
        onClose={cerrarFormulario}
        onGuardado={recargar}
      />

      {/* Ítem L · diálogos de acción */}
      <SalidaConfirmarModal
        accion={acciones.dialogo.confirmar?.accion ?? null}
        salida={acciones.dialogo.confirmar?.salida ?? null}
        enviando={acciones.enviando}
        errorServidor={acciones.errorAccion}
        onClose={acciones.cerrarDialogo}
        onConfirmar={() => void confirmarAccionSimple()}
      />

      <SalidaRechazarModal
        salida={acciones.dialogo.rechazar}
        enviando={acciones.enviando}
        errorServidor={acciones.errorAccion}
        onClose={acciones.cerrarDialogo}
        onRechazar={async (motivo) => {
          const fallo = await acciones.rechazar(motivo);
          if (!fallo) acciones.cerrarDialogo();
          return fallo;
        }}
      />

      <SalidaNovedadModal
        salida={acciones.dialogo.novedad}
        enviando={acciones.enviando}
        errorServidor={acciones.errorAccion}
        onClose={acciones.cerrarDialogo}
        onGuardar={async (payload) => {
          const fallo = await acciones.guardarNovedad(payload);
          if (!fallo) acciones.cerrarDialogo();
          return fallo;
        }}
        onEliminar={async () => {
          const fallo = await acciones.eliminarNovedad();
          if (!fallo) acciones.cerrarDialogo();
          return fallo;
        }}
      />

      <SalidaHistorialModal
        salida={acciones.dialogo.historial}
        onClose={acciones.cerrarDialogo}
      />

      <SalidaAprobarLoteModal
        cantidad={acciones.dialogo.lote ? acciones.seleccionCantidad : null}
        enviando={acciones.enviando}
        errorServidor={acciones.errorAccion}
        onClose={acciones.cerrarDialogo}
        onConfirmar={confirmarLote}
      />
    </div>
  );
};

export default SalidasView;
