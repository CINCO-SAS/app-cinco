// src/modules/transporte/informes/components/InformeWfmRefresh.tsx
//
// Botón de refresco WFM para el bloque "Reporte Área" (legacy: ícono de
// recarga que aparecía solo cuando el área era "I&M").
//
// QUÉ HACE: lanza `POST /wfm/validar/` con el mes/año actual y el área.
// El endpoint ESCRIBE validaciones (REPORTADO → VALIDADO), por lo que:
//   1. Solo aparece para el área "I&M" (como el legacy).
//   2. Antes de ejecutar muestra un modal de confirmación.
//   3. Requiere permiso `change_salida` en el servidor — si el usuario no
//      tiene permisos recibirá un 403 con mensaje claro.
//
// PAYLOAD: replica el contrato de `WfmLoteSerializer`:
//   { mes, yyyy, area } — sin fecha_inicio/fecha_fin, usa el mes completo.
//
// MANEJO DE PERMISOS EN CLIENTE: no se hace fetching previo de permisos
// para decidir si mostrar/ocultar el botón; el servidor es la única fuente
// de verdad (401/403 se capturan y se muestran en el modal). El legacy
// tampoco lo hacía: el token HMAC solo prevenía llamadas externas, no
// filtraba por rol en el front.

import { useState } from "react";

import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";

/** Área que habilita el botón de refresco WFM (igual que el legacy). */
const AREA_WFM = "I&M";

const BOTON_WFM =
  "h-8 rounded-lg border border-blue-300 bg-blue-50 px-2.5 text-xs font-medium " +
  "text-blue-700 transition hover:bg-blue-100 disabled:cursor-not-allowed " +
  "disabled:opacity-60 focus:border-blue-500 focus:outline-none focus:ring-2 " +
  "focus:ring-blue-500/20 dark:border-blue-700 dark:bg-blue-900/30 " +
  "dark:text-blue-300 dark:hover:bg-blue-900/50";

const BOTON_MODAL_OK =
  "rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white " +
  "hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 " +
  "focus:outline-none focus:ring-2 focus:ring-blue-500/30";

const BOTON_MODAL_CANCEL =
  "rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium " +
  "text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 " +
  "focus:ring-gray-200 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

interface InformeWfmRefreshProps {
  /** Área a la que pertenece este bloque — el botón solo aparece para "I&M". */
  area: string;
  mes: number;
  anio: number;
  /** Callback para refrescar la tabla tras la validación. */
  onValidado?: () => void;
}

interface ResultadoWfm {
  updated_count?: number;
  total_reportados?: number;
  has_more_in_chunk?: boolean;
}

export const InformeWfmRefresh = ({
  area,
  mes,
  anio,
  onValidado,
}: InformeWfmRefreshProps) => {
  const [modalAbierto, setModalAbierto] = useState(false);
  const [validando, setValidando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoWfm | null>(null);

  // Solo el área I&M muestra el botón (igual que el legacy).
  if (area !== AREA_WFM) return null;

  const abrir = () => {
    setError(null);
    setResultado(null);
    setModalAbierto(true);
  };

  const cerrar = () => {
    setModalAbierto(false);
    setError(null);
    setResultado(null);
  };

  const confirmar = async () => {
    setValidando(true);
    setError(null);
    try {
      const res = await transporteService.validarWfm({
        mes,
        yyyy: anio,
        area,
      });
      const data = res as unknown as ResultadoWfm;
      setResultado(data);
      onValidado?.();
    } catch (err) {
      const apiError = err as ApiError;
      setError(
        apiError?.message ??
          "No fue posible lanzar la validación WFM. Verifica que tienes el permiso de gestión.",
      );
      logDevelopmentError("Error en validación WFM:", err);
    } finally {
      setValidando(false);
    }
  };

  return (
    <>
      <button
        id="btn-wfm-refresh-im"
        type="button"
        onClick={abrir}
        className={BOTON_WFM}
        title="Lanzar validación WFM masiva para I&M (requiere permiso de gestión)."
      >
        ↻ WFM
      </button>

      {/* Modal de confirmación */}
      {modalAbierto && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="wfm-modal-titulo"
        >
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-800 dark:bg-gray-900">
            <h2
              id="wfm-modal-titulo"
              className="mb-2 text-base font-semibold text-gray-800 dark:text-white/90"
            >
              Validación WFM — I&amp;M
            </h2>

            {!resultado ? (
              <>
                <p className="mb-1 text-sm text-gray-600 dark:text-gray-300">
                  Esta acción validará{" "}
                  <strong>masivamente</strong> todas las salidas en estado{" "}
                  <strong>REPORTADO</strong> del área <strong>I&amp;M</strong>{" "}
                  para{" "}
                  <strong>
                    {mes.toString().padStart(2, "0")}/{anio}
                  </strong>{" "}
                  que tengan respaldo en WFM o agenda.
                </p>
                <p className="mb-4 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                  Las salidas validadas pasarán a estado <strong>VALIDADO</strong>{" "}
                  y no podrán revertirse desde aquí. Esta acción requiere
                  permiso de gestión.
                </p>

                {error && (
                  <p className="mb-3 rounded-lg bg-error-50 px-3 py-2 text-xs text-error-700 dark:bg-error-900/30 dark:text-error-300">
                    {error}
                  </p>
                )}

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={cerrar}
                    disabled={validando}
                    className={BOTON_MODAL_CANCEL}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    onClick={() => void confirmar()}
                    disabled={validando}
                    className={BOTON_MODAL_OK}
                  >
                    {validando ? "Validando…" : "Confirmar validación"}
                  </button>
                </div>
              </>
            ) : (
              /* Pantalla de resultado */
              <>
                <div className="mb-4 rounded-lg bg-success-50 px-4 py-3 dark:bg-success-900/30">
                  <p className="text-sm font-semibold text-success-700 dark:text-success-300">
                    Validación completada
                  </p>
                  {resultado.updated_count !== undefined && (
                    <p className="mt-1 text-sm text-success-600 dark:text-success-400">
                      {resultado.updated_count} salida
                      {resultado.updated_count !== 1 ? "s" : ""} validadas.
                    </p>
                  )}
                  {resultado.has_more_in_chunk && (
                    <p className="mt-1 text-xs text-warning-600 dark:text-warning-400">
                      Hay más salidas pendientes. Vuelve a lanzar WFM para
                      continuar, o espera al worker automático.
                    </p>
                  )}
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={cerrar}
                    className={BOTON_MODAL_CANCEL}
                  >
                    Cerrar
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
};
