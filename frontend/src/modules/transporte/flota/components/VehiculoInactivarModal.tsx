// src/modules/transporte/flota/components/VehiculoInactivarModal.tsx
//
// Baja lógica de un vehículo vehicular (F2 · §5.4).
//
// A diferencia del legacy (que borraba el registro físico o fallaba por FK con salidas),
// aquí el vehículo queda con `activo=false` y conserva todo su historial documental y operativo.

"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import { Modal } from "@/components/ui/modal";
import { classifyError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { VehiculoListado } from "@/types/transporte.types";

interface VehiculoInactivarModalProps {
  /** `null` → cerrado. */
  vehiculo: VehiculoListado | null;
  onClose: () => void;
  onInactivado: () => void;
}

export const VehiculoInactivarModal = ({
  vehiculo,
  onClose,
  onInactivado,
}: VehiculoInactivarModalProps) => {
  const abierto = vehiculo !== null;
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const confirmar = useCallback(async () => {
    if (!vehiculo) return;

    setEnviando(true);
    setErrorServidor(null);
    try {
      await transporteService.inactivarVehiculo(vehiculo.id);
      toast.success(`Vehículo con placa ${vehiculo.placa} inactivado con éxito.`);
      onInactivado();
      onClose();
    } catch (error) {
      const detalle = classifyError(error);
      setErrorServidor(detalle.message);
      logDevelopmentError("Error inactivando vehículo:", error);
    } finally {
      setEnviando(false);
    }
  }, [vehiculo, onInactivado, onClose]);

  return (
    <Modal
      isOpen={abierto}
      onClose={() => {
        if (!enviando) onClose();
      }}
      className="max-w-md"
      title="vehiculo-inactivar-titulo"
    >
      <div className="px-5 pt-5 pb-1 pr-16">
        <h2
          id="vehiculo-inactivar-titulo"
          className="text-base font-semibold text-gray-800 dark:text-white/90"
        >
          Inactivar vehículo
        </h2>
      </div>

      <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
        {errorServidor && (
          <Alert variant="error" title="No se pudo inactivar" message={errorServidor} />
        )}

        <p className="text-sm text-gray-600 dark:text-gray-300">
          ¿Estás seguro de que deseas inactivar el vehículo con placa{" "}
          <span className="font-bold text-gray-800 dark:text-white/90">
            {vehiculo?.placa}
          </span>{" "}
          ({vehiculo?.marca} {vehiculo?.referencia ?? ""})?
        </p>

        <p className="text-xs text-gray-500 dark:text-gray-400">
          El vehículo ya no aparecerá en el catálogo operativo para nuevas salidas,
          pero se conservará su historial de despachos y liquidaciones.
        </p>
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
