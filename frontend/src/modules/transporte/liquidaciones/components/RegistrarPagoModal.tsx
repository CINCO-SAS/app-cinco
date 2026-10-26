// src/modules/transporte/liquidaciones/components/RegistrarPagoModal.tsx
//
// Modal para registrar o marcar el pago mensual de un vehículo (A2 / D3).

"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/modal/Modal";
import Button from "@/components/ui/button/Button";
import Alert from "@/components/ui/alert/Alert";
import { classifyError } from "@/lib/errorHandler";
import type { RegistrarPagoPayload, SabanaFila } from "@/types/transporte.types";

interface RegistrarPagoModalProps {
  fila: SabanaFila | null;
  mes: number;
  anio: number;
  tipo: "pago-mensual" | "pronto-pago";
  isOpen: boolean;
  onClose: () => void;
  onGuardar: (payload: RegistrarPagoPayload) => Promise<void>;
}

const hoyISO = (): string => {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const CLASES_INPUT =
  "h-11 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "placeholder:text-gray-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

export const RegistrarPagoModal: React.FC<RegistrarPagoModalProps> = ({
  fila,
  mes,
  anio,
  tipo,
  isOpen,
  onClose,
  onGuardar,
}) => {
  const [pagado, setPagado] = useState<boolean>(fila?.pagado ?? true);
  const [fechaPago, setFechaPago] = useState<string>(
    fila?.fecha_pago ?? hoyISO(),
  );
  const [totalLiquidado, setTotalLiquidado] = useState<string>(
    fila ? String(fila.total_liquidado || fila.total) : "0",
  );
  const [enviando, setEnviando] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!fila) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnviando(true);
    setError(null);

    try {
      await onGuardar({
        vehiculo: fila.vehiculo,
        mes,
        anio,
        tipo: tipo === "pronto-pago" ? "PRONTO_PAGO" : "MENSUAL",
        pagado,
        fecha_pago: pagado ? fechaPago : undefined,
        total_liquidado: Number(totalLiquidado) || undefined,
      });
      onClose();
    } catch (err) {
      setError(classifyError(err).message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-md">
      <form onSubmit={handleSubmit} noValidate className="p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Registrar Pago de Vehículo
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Vehículo placa{" "}
            <span className="font-mono font-bold text-gray-900 dark:text-white">
              {fila.placa}
            </span>{" "}
            · Período {mes}/{anio}
          </p>
        </div>

        {error && (
          <Alert variant="error" title="No se pudo registrar" message={error} />
        )}

        <div className="rounded-xl bg-gray-50 p-3.5 dark:bg-gray-800/60 text-xs space-y-1.5">
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Días liquidados:</span>
            <span className="font-semibold text-gray-800 dark:text-gray-200">
              {fila.dias} días
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500 dark:text-gray-400">Valor día base:</span>
            <span className="font-semibold text-gray-800 dark:text-gray-200">
              ${Number(fila.valor_dia).toLocaleString("es-CO")}
            </span>
          </div>
          <div className="flex justify-between border-t border-gray-200 pt-1.5 dark:border-gray-700">
            <span className="text-gray-700 font-medium dark:text-gray-300">
              Total Calculado:
            </span>
            <span className="font-bold text-brand-600 dark:text-brand-400 text-sm">
              ${Number(fila.total).toLocaleString("es-CO")}
            </span>
          </div>
        </div>

        {/* Estado pagado */}
        <div className="flex items-center gap-3 pt-1">
          <input
            id="pago-checkbox"
            type="checkbox"
            checked={pagado}
            onChange={(e) => setPagado(e.target.checked)}
            disabled={enviando}
            className="h-4 w-4 rounded border-gray-300 text-brand-500 focus:ring-brand-500/20"
          />
          <label
            htmlFor="pago-checkbox"
            className="text-sm font-medium text-gray-800 dark:text-gray-200"
          >
            Marcar como efectivamente pagado
          </label>
        </div>

        {pagado && (
          <div>
            <label
              htmlFor="pago-fecha"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
            >
              Fecha de pago <span className="text-error-500">*</span>
            </label>
            <input
              id="pago-fecha"
              type="date"
              value={fechaPago}
              onChange={(e) => setFechaPago(e.target.value)}
              disabled={enviando}
              required
              className={CLASES_INPUT}
            />
          </div>
        )}

        <div>
          <label
            htmlFor="pago-monto"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
          >
            Importe total liquidado ($ COP)
          </label>
          <input
            id="pago-monto"
            type="number"
            value={totalLiquidado}
            onChange={(e) => setTotalLiquidado(e.target.value)}
            disabled={enviando}
            step="100"
            min="0"
            className={CLASES_INPUT}
          />
        </div>

        <div className="flex justify-end gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
          <Button
            id="pago-modal-btn-cancelar"
            variant="outline"
            type="button"
            onClick={onClose}
            disabled={enviando}
          >
            Cancelar
          </Button>
          <Button
            id="pago-modal-btn-guardar"
            variant="primary"
            type="submit"
            disabled={enviando || (pagado && !fechaPago)}
          >
            {enviando ? "Guardando..." : "Guardar Pago"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
