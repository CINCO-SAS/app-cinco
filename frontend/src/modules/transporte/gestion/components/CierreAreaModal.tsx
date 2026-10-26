// src/modules/transporte/gestion/components/CierreAreaModal.tsx
//
// Modal para registrar el cierre mensual de validación de salidas por área (F4 / B4).
// Exige ser Jefe Validador del área o tener permiso de programación/admin.

"use client";

import React, { useState } from "react";
import { toast } from "sonner";

import { Modal } from "@/components/ui/modal/Modal";
import Button from "@/components/ui/button/Button";
import Alert from "@/components/ui/alert/Alert";
import { classifyError } from "@/lib/errorHandler";
import { transporteService } from "@/services/transporte.service";

interface CierreAreaModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGuardado: () => void;
  mesDefecto: number;
  anioDefecto: number;
}

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

const CLASES_INPUT =
  "h-11 w-full rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "placeholder:text-gray-400 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

export const CierreAreaModal: React.FC<CierreAreaModalProps> = ({
  isOpen,
  onClose,
  onGuardado,
  mesDefecto,
  anioDefecto,
}) => {
  const [area, setArea] = useState<string>("");
  const [mes, setMes] = useState<number>(mesDefecto);
  const [anio, setAnio] = useState<number>(anioDefecto);
  const [observaciones, setObservaciones] = useState<string>("");
  const [enviando, setEnviando] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const areaLimpia = area.trim().toUpperCase();
    if (!areaLimpia) {
      setError("Debe especificar el nombre del área a cerrar.");
      return;
    }

    setEnviando(true);
    setError(null);

    try {
      await transporteService.cerrarArea({
        area: areaLimpia,
        mes,
        anio,
        datos: observaciones.trim()
          ? { observacion_cierre: observaciones.trim() }
          : undefined,
      });

      toast.success(`Cierre mensual registrado con éxito para el área ${areaLimpia}.`);
      onGuardado();
      onClose();
      setArea("");
      setObservaciones("");
    } catch (err) {
      const msg = classifyError(err).message;
      setError(msg);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="max-w-lg">
      <form onSubmit={handleSubmit} noValidate className="p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Cierre Mensual de Validación por Área
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Formaliza el visto bueno de las salidas del área para el período seleccionado.
            Esta acción certifica las salidas ante nómina y liquidación.
          </p>
        </div>

        {error && (
          <Alert variant="error" title="No se pudo registrar el cierre" message={error} />
        )}

        {/* Nombre del área */}
        <div>
          <label
            htmlFor="cierre-area"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
          >
            Nombre del Área <span className="text-error-500">*</span>
          </label>
          <input
            id="cierre-area"
            type="text"
            value={area}
            onChange={(e) => setArea(e.target.value.toUpperCase())}
            placeholder="Ej: OPERACIONES, LOGISTICA, ENERGIA"
            disabled={enviando}
            autoFocus
            className={CLASES_INPUT}
          />
        </div>

        {/* Período Mes y Año */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="cierre-mes"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
            >
              Mes <span className="text-error-500">*</span>
            </label>
            <select
              id="cierre-mes"
              value={mes}
              onChange={(e) => setMes(Number(e.target.value))}
              disabled={enviando}
              className={CLASES_INPUT}
            >
              {MESES.map((nombre, idx) => (
                <option key={nombre} value={idx + 1}>
                  {idx + 1} - {nombre}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="cierre-anio"
              className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
            >
              Año <span className="text-error-500">*</span>
            </label>
            <input
              id="cierre-anio"
              type="number"
              value={anio}
              min={2020}
              max={2035}
              onChange={(e) => setAnio(Number(e.target.value))}
              disabled={enviando}
              className={CLASES_INPUT}
            />
          </div>
        </div>

        {/* Observaciones */}
        <div>
          <label
            htmlFor="cierre-observaciones"
            className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-400"
          >
            Observaciones o Novedad de Cierre (Opcional)
          </label>
          <textarea
            id="cierre-observaciones"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
            placeholder="Notas adicionales sobre la validación de este período..."
            disabled={enviando}
            rows={3}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90"
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button
            id="cierre-modal-btn-cancelar"
            variant="outline"
            type="button"
            onClick={onClose}
            disabled={enviando}
          >
            Cancelar
          </Button>
          <Button
            id="cierre-modal-btn-guardar"
            variant="primary"
            type="submit"
            disabled={enviando || !area.trim()}
          >
            {enviando ? "Guardando..." : "Confirmar Cierre"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
