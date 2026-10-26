// src/modules/transporte/liquidaciones/liquidacionesView.hooks.ts
//
// Hooks de lógica para Liquidaciones Financieras (A2 / D3 / D4 / CR-10).
// Controla sábanas de pago mensual vs pronto pago, cálculo de consecutivos y marcas de pago.

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { classifyError } from "@/lib/errorHandler";
import { transporteService } from "@/services/transporte.service";
import type {
  RegistrarPagoPayload,
  SabanaLiquidacion,
} from "@/types/transporte.types";

export type TipoSabana = "pago-mensual" | "pronto-pago";

export function useLiquidacionesState() {
  const d = new Date();
  const [mes, setMes] = useState<number>(d.getMonth() + 1);
  const [anio, setAnio] = useState<number>(d.getFullYear());
  const [tipo, setTipo] = useState<TipoSabana>("pago-mensual");
  const [placa, setPlaca] = useState<string>("");

  const [sabana, setSabana] = useState<SabanaLiquidacion | null>(null);
  const [cargando, setCargando] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const consultar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await transporteService.getSabana({
        mes,
        anio,
        tipo,
        placa: placa.trim().toUpperCase() || undefined,
      });
      setSabana(data);
    } catch (err) {
      const msg = classifyError(err).message;
      setError(msg);
    } finally {
      setCargando(false);
    }
  }, [mes, anio, tipo, placa]);

  useEffect(() => {
    void consultar();
  }, [consultar]);

  const abrirCuentaCobro = useCallback(
    (placaVehiculo: string) => {
      const url = `/api/v1/transporte/informes/cuenta-cobro/?placa=${encodeURIComponent(
        placaVehiculo,
      )}&mes=${mes}&anio=${anio}`;
      window.open(url, "_blank");
    },
    [mes, anio],
  );

  const registrarPagoVehiculo = useCallback(
    async (payload: RegistrarPagoPayload) => {
      try {
        await transporteService.registrarPago(payload);
        toast.success("Pago registrado exitosamente en el sistema.");
        await consultar();
      } catch (err) {
        const msg = classifyError(err).message;
        toast.error(`Error al registrar pago: ${msg}`);
        throw err;
      }
    },
    [consultar],
  );

  const generarConsecutivoVehiculo = useCallback(
    async (vehiculoId: number) => {
      try {
        const res = await transporteService.generarConsecutivo({
          vehiculo: vehiculoId,
          mes,
          anio,
        });
        toast.success(
          `Consecutivo #${res.consecutivo} ${
            res.creado ? "generado" : "existente"
          } para el vehículo.`,
        );
        await consultar();
      } catch (err) {
        const msg = classifyError(err).message;
        toast.error(`Error al generar consecutivo: ${msg}`);
      }
    },
    [mes, anio, consultar],
  );

  return {
    mes,
    setMes,
    anio,
    setAnio,
    tipo,
    setTipo,
    placa,
    setPlaca,
    sabana,
    cargando,
    error,
    recargar: consultar,
    abrirCuentaCobro,
    registrarPagoVehiculo,
    generarConsecutivoVehiculo,
  };
}
