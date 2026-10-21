// src/modules/transporte/operacion/salidas/components/SalidaHistorialModal.tsx
//
// Ítem L · trazabilidad de estados de una salida (B4 · §7.2).
//
// El legacy guardaba el historial como un JSON dentro de un `longtext` en la
// fila: ilegible, imposible de consultar y se perdía al editar la salida.
// Aquí es una tabla de filas (`transporte_salida_historial`) y esto solo las
// pinta, de más reciente a más antiguo.
//
// El `motivo` es el texto que escribió quien rechazó/aprobó: es la razón de
// ser de esta pantalla. Sin eso, un rechazo es un mero cambio de color.

"use client";

import { useEffect, useState } from "react";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";
import { classifyError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import { BadgeEstadoSalida, formatearFechaCorta } from "../salidasView.utils";
import type { Salida, SalidaHistorial } from "@/types/transporte.types";

export interface SalidaHistorialModalProps {
  /** `null` → cerrado. */
  salida: Salida | null;
  onClose: () => void;
}

/** `2026-03-14T10:22:31Z` → `14/03/2026 10:22`. Sin conversión de zona. */
const formatearMomento = (iso?: string | null): string => {
  if (!iso) return "—";
  const [fecha, hora] = iso.split("T");
  const soloHora = hora ? hora.slice(0, 5) : "";
  return `${formatearFechaCorta(fecha)}${soloHora ? ` ${soloHora}` : ""}`;
};

export const SalidaHistorialModal = ({
  salida,
  onClose,
}: SalidaHistorialModalProps) => {
  const abierto = salida !== null;
  const [filas, setFilas] = useState<SalidaHistorial[]>([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cada apertura re-consulta: el historial puede haber crecido desde la
  // última vez que se miró esta salida.
  useEffect(() => {
    if (!abierto || !salida) return;
    let vivo = true;
    setCargando(true);
    setError(null);
    transporteService
      .getHistorialSalida(salida.id)
      .then((filas) => {
        if (vivo) setFilas(filas);
      })
      .catch((err: unknown) => {
        if (!vivo) return;
        setError(classifyError(err).message);
        logDevelopmentError("Error cargando historial de salida:", err);
      })
      .finally(() => {
        if (vivo) setCargando(false);
      });
    return () => {
      vivo = false;
    };
  }, [abierto, salida]);

  return (
    <Modal
      isOpen={abierto}
      onClose={onClose}
      className="max-w-lg"
      title="salida-historial-titulo"
    >
      <div className="px-5 pt-5 pb-1 pr-16">
        <h2
          id="salida-historial-titulo"
          className="text-base font-semibold text-gray-800 dark:text-white/90"
        >
          Historial de la salida
        </h2>
        {salida && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {salida.vehiculo_placa} · {formatearFechaCorta(salida.fecha_salida)}
          </p>
        )}
      </div>

      <div className="max-h-[60vh] overflow-y-auto px-5 pt-4 pb-2">
        {error && (
          <Alert variant="error" title="No se pudo cargar" message={error} />
        )}

        {!error && cargando && (
          <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
            Cargando historial...
          </p>
        )}

        {!error && !cargando && filas.length === 0 && (
          <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
            Esta salida aún no tiene cambios de estado registrados.
          </p>
        )}

        {!error && !cargando && filas.length > 0 && (
          <ol className="space-y-3">
            {filas.map((fila) => (
              <li
                key={fila.id}
                className="rounded-lg border border-gray-200 p-3 dark:border-gray-800"
              >
                <div className="flex items-center justify-between gap-3">
                  <BadgeEstadoSalida estado={fila.estado} />
                  <span className="whitespace-nowrap text-xs text-gray-400 dark:text-gray-500">
                    {formatearMomento(fila.fecha_cambio)}
                  </span>
                </div>
                {fila.motivo && (
                  <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                    {fila.motivo}
                  </p>
                )}
                {fila.creado_por_cedula && (
                  <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                    Registrado por CC {fila.creado_por_cedula}
                  </p>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="flex items-center justify-end border-t border-gray-200 px-5 py-4 dark:border-gray-800">
        <Button type="button" variant="outline" onClick={onClose}>
          Cerrar
        </Button>
      </div>
    </Modal>
  );
};
