// src/modules/transporte/operacion/kiosco/kioscoView.hooks.ts
//
// Estado y lógica del flujo Kiosco (S1 -> S3 -> S6):
//   Paso 1: identificar vehículo por placa o QR
//   Paso 2: pre-chequeo S3 (validar fecha/vehículo/móvil)
//   Paso 3: registrar salida S6 + confirmación

import { useCallback, useState } from "react";
import { toast } from "sonner";

import { classifyError } from "@/lib/errorHandler";
import { transporteService } from "@/services/transporte.service";
import type {
  KioscoDatoVehiculo,
  KioscoResultadoValidacion,
  RegistrarSalidaPayload,
  Salida,
} from "@/types/transporte.types";

// --------------------------------------------------------------------------
// Tipos del hook
// --------------------------------------------------------------------------

export type PasoKiosco =
  | "IDLE"
  | "CARGANDO"
  | "IDENTIFICADO"
  | "VALIDANDO"
  | "VALIDADO"
  | "REGISTRANDO"
  | "REGISTRADO"
  | "ERROR";

export interface EstadoKiosco {
  paso: PasoKiosco;
  placa: string;
  datos: KioscoDatoVehiculo | null;
  movilSale: string;
  area: string;
  fecha: string;
  validacion: KioscoResultadoValidacion | null;
  salidaRegistrada: Salida | null;
  error: string | null;
}

const hoy = (): string => {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

const ESTADO_INICIAL: EstadoKiosco = {
  paso: "IDLE",
  placa: "",
  datos: null,
  movilSale: "",
  area: "",
  fecha: hoy(),
  validacion: null,
  salidaRegistrada: null,
  error: null,
};

// --------------------------------------------------------------------------
// Hook
// --------------------------------------------------------------------------

export function useKioscoState() {
  const [estado, setEstado] = useState<EstadoKiosco>(ESTADO_INICIAL);

  const reiniciar = useCallback(() => setEstado(ESTADO_INICIAL), []);

  const setPlaca = useCallback(
    (placa: string) =>
      setEstado((prev) => ({ ...prev, placa: placa.toUpperCase().trim() })),
    [],
  );

  const setFecha = useCallback(
    (fecha: string) => setEstado((prev) => ({ ...prev, fecha })),
    [],
  );

  const setMovilSale = useCallback(
    (movil: string) => setEstado((prev) => ({ ...prev, movilSale: movil })),
    [],
  );

  const setArea = useCallback(
    (area: string) => setEstado((prev) => ({ ...prev, area })),
    [],
  );

  // Paso 1 - Identificar vehículo (S1/S4)
  const identificar = useCallback(
    async (placaParam?: string) => {
      const placaFinal = (placaParam ?? estado.placa).toUpperCase().trim();
      if (!placaFinal) return;

      setEstado((prev) => ({
        ...prev,
        paso: "CARGANDO",
        placa: placaFinal,
        error: null,
      }));

      try {
        const res = await transporteService.identificarVehiculo({ placa: placaFinal });
        const respuesta = res as {
          ok: boolean;
          data?: KioscoDatoVehiculo;
          error?: string;
        };

        if (!respuesta.ok || !respuesta.data) {
          throw new Error(respuesta.error ?? "Vehículo no encontrado en el catálogo.");
        }

        setEstado((prev) => ({
          ...prev,
          paso: "IDENTIFICADO",
          datos: respuesta.data ?? null,
          error: null,
        }));
      } catch (err) {
        const msg = classifyError(err).message;
        setEstado((prev) => ({ ...prev, paso: "ERROR", error: msg }));
      }
    },
    [estado.placa],
  );

  // Paso 2 - Pre-chequeo S3
  const validar = useCallback(async () => {
    const vehiculoId = estado.datos?.vehiculo?.id;
    if (!vehiculoId || !estado.fecha) return;

    setEstado((prev) => ({ ...prev, paso: "VALIDANDO", error: null }));

    try {
      const res = await transporteService.validarKiosco({
        fecha: estado.fecha,
        vehiculo: vehiculoId,
        movil_sale: estado.movilSale.trim() || undefined,
      });

      const respuesta = res as {
        ok: boolean;
        data?: KioscoResultadoValidacion;
        error?: string;
      };

      if (!respuesta.ok) {
        throw new Error(respuesta.error ?? "Error en la validación del vehículo.");
      }

      setEstado((prev) => ({
        ...prev,
        paso: "VALIDADO",
        validacion: respuesta.data ?? null,
        error: null,
      }));
    } catch (err) {
      const msg = classifyError(err).message;
      setEstado((prev) => ({ ...prev, paso: "ERROR", error: msg }));
    }
  }, [estado.datos, estado.fecha, estado.movilSale]);

  // Paso 3 - Registrar salida S6
  const registrar = useCallback(
    async (camposExtra?: Partial<RegistrarSalidaPayload>) => {
      const vehiculoId = estado.datos?.vehiculo?.id;
      if (!vehiculoId) return;

      setEstado((prev) => ({ ...prev, paso: "REGISTRANDO", error: null }));

      try {
        const movilLimpio = estado.movilSale.trim();
        const esDisponible = !movilLimpio || movilLimpio.toLowerCase() === "disponible";

        const payload: RegistrarSalidaPayload = {
          fecha_salida: estado.fecha,
          vehiculo: vehiculoId,
          movil_sale: esDisponible ? "disponible" : movilLimpio,
          area: estado.area.trim() || undefined,
          ...camposExtra,
        };

        const salida = await transporteService.registrarSalida(payload);

        toast.success("Salida registrada exitosamente en estado Reportado.");

        setEstado((prev) => ({
          ...prev,
          paso: "REGISTRADO",
          salidaRegistrada: salida,
          error: null,
        }));
      } catch (err) {
        const msg = classifyError(err).message;
        setEstado((prev) => ({ ...prev, paso: "ERROR", error: msg }));
      }
    },
    [estado.datos, estado.fecha, estado.movilSale, estado.area],
  );

  const volverAIdentificado = useCallback(() => {
    setEstado((prev) => ({
      ...prev,
      paso: "IDENTIFICADO",
      validacion: null,
      error: null,
    }));
  }, []);

  return {
    estado,
    reiniciar,
    setPlaca,
    setFecha,
    setMovilSale,
    setArea,
    identificar,
    validar,
    registrar,
    volverAIdentificado,
  };
}
