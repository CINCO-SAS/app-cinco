// src/modules/transporte/conductores/components/ConductorInactivarModal.tsx
//
// Baja lógica de un conductor (F2 · §5.4).
//
// El backend EXIGE `fecha_egreso` para inactivar (no es opcional): sin ella
// responde 400 `{"ok":false,"error":...}`. Por eso el modal no es una simple
// confirmación: pide la fecha y la envía en el cuerpo del `POST
// /conductores/{id}/inactivar/`.
//
// A diferencia del legacy (que BORRABA el registro y perdía el historial de
// salidas), aquí el conductor queda con `activo=false`.

"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import { Modal } from "@/components/ui/modal";
import { classifyError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { ConductorListado } from "@/types/transporte.types";

interface ConductorInactivarModalProps {
  /** `null` → cerrado. */
  conductor: ConductorListado | null;
  onClose: () => void;
  onInactivado: () => void;
}

/** `YYYY-MM-DD` de hoy, sin desfase horario (D-A4). */
const hoyISO = (): string => {
  const ahora = new Date();
  const anio = ahora.getFullYear();
  const mes = String(ahora.getMonth() + 1).padStart(2, "0");
  const dia = String(ahora.getDate()).padStart(2, "0");
  return `${anio}-${mes}-${dia}`;
};

export const ConductorInactivarModal = ({
  conductor,
  onClose,
  onInactivado,
}: ConductorInactivarModalProps) => {
  const abierto = conductor !== null;
  const [fechaEgreso, setFechaEgreso] = useState(hoyISO);
  const [errorFecha, setErrorFecha] = useState<string | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (abierto) {
      setFechaEgreso(hoyISO());
      setErrorFecha(null);
      setErrorServidor(null);
    }
  }, [abierto, conductor?.id]);

  const confirmar = useCallback(async () => {
    if (!conductor) return;

    if (!fechaEgreso) {
      setErrorFecha("La fecha de egreso es obligatoria.");
      return;
    }

    setEnviando(true);
    setErrorServidor(null);
    try {
      await transporteService.inactivarConductor(conductor.id, fechaEgreso);
      toast.success(`${conductor.nombre_completo} quedó inactivo.`);
      onInactivado();
      onClose();
    } catch (error) {
      const detalle = classifyError(error);
      setErrorServidor(detalle.message);
      logDevelopmentError("Error inactivando conductor:", error);
    } finally {
      setEnviando(false);
    }
  }, [conductor, fechaEgreso, onInactivado, onClose]);

  return (
    <Modal
      isOpen={abierto}
      onClose={() => {
        if (!enviando) onClose();
      }}
      className="max-w-md"
      // `title` NO es texto visible: Modal lo usa como `aria-labelledby`.
      title="conductor-inactivar-titulo"
    >
      {/* Padding horizontal: `Modal` no lo aporta; `pr-16` evita el botón de
          cerrar que va absoluto en la esquina superior derecha. */}
      <div className="px-5 pt-5 pb-1 pr-16">
        <h2
          id="conductor-inactivar-titulo"
          className="text-base font-semibold text-gray-800 dark:text-white/90"
        >
          Inactivar conductor
        </h2>
      </div>

      <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
        {errorServidor && (
          <Alert variant="error" title="No se pudo inactivar" message={errorServidor} />
        )}

        <p className="text-sm text-gray-600 dark:text-gray-300">
          Vas a inactivar a{" "}
          <span className="font-medium text-gray-800 dark:text-white/90">
            {conductor?.nombre_completo}
          </span>{" "}
          (cédula {conductor?.cedula}). El registro se conserva con su historial;
          solo cambia el estado a inactivo.
        </p>

        <div>
          <Label htmlFor="conductor-egreso">
            Fecha de egreso <span className="text-error-500">*</span>
          </Label>
          <Input
            id="conductor-egreso"
            type="date"
            value={fechaEgreso}
            onChange={(e) => {
              setFechaEgreso(e.target.value);
              setErrorFecha(null);
            }}
            disabled={enviando}
            error={Boolean(errorFecha)}
            hint={errorFecha ?? undefined}
          />
        </div>
      </div>

      <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
        <Button
          type="button"
          variant="outline"
          onClick={onClose}
          disabled={enviando}
        >
          Cancelar
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={() => void confirmar()}
          disabled={enviando}
        >
          {enviando ? "Inactivando..." : "Inactivar"}
        </Button>
      </div>
    </Modal>
  );
};
