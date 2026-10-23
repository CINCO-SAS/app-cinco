// src/modules/transporte/informes/components/InformeCuentaCobro.tsx
//
// Bloque "Cuenta de Cobro" (Paso 7): `GET /informes/cuenta-cobro/` (F5-1)
// — el documento imprimible del alquiler del vehículo para el periodo, que
// el navegador abre en pestaña nueva para imprimir a PDF.
//
// SE ABRE COMO HTML DEL SERVIDOR, no como ruta del front: el endpoint
// devuelve un documento completo (con su CSS de impresión) y requiere
// autenticación, así que no sirve un `window.open(url)` a secas — iría 401
// sin el Bearer. La pestaña se abre ANTES del `await` (los bloqueadores de
// popups solo aceptan `window.open` sin red en medio), y una vez con la
// respuesta se le escribe el documento con `document.write`.
//
// EL IMPORTE, EL PAGADOR Y EL CONSECUTIVO se calculan EN SERVIDOR desde las
// salidas del mes: aquí solo viajan placa + periodo. El legacy los leía de
// campos ocultos del formulario, manipulables desde el navegador.
//
// Las placas salen de la liquidación del mes (mismo hook): la cuenta de
// cobro se calcula desde esas salidas, así que un vehículo sin filas en el
// periodo no tiene cuenta que mostrar.

import { useMemo, useState } from "react";

import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { FilaLiquidacionInforme } from "@/types/transporte.types";
import { BOTON_CLASES, SELECT_CLASES } from "./InformeToolbar";

interface InformeCuentaCobroProps {
  mes: number;
  anio: number;
  /** Vehículos del periodo (de la liquidación): de aquí salen las placas. */
  vehiculos: FilaLiquidacionInforme[];
}

export const InformeCuentaCobro = ({
  mes,
  anio,
  vehiculos,
}: InformeCuentaCobroProps) => {
  const [placa, setPlaca] = useState("");
  const [abriendo, setAbriendo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const opciones = useMemo(
    () => [...vehiculos].sort((a, b) => a.placa.localeCompare(b.placa)),
    [vehiculos],
  );

  const abrir = async () => {
    if (!placa || abriendo) return;

    // ANTES del await: un window.open posterior al fetch es una ventana
    // bloqueada en la mayoría de navegadores.
    const ventana = window.open("", "_blank");
    if (!ventana) {
      setError(
        "El navegador bloqueó la pestaña nueva. Habilítela para ver la cuenta de cobro.",
      );
      return;
    }
    ventana.document.title = `Cuenta de cobro ${placa}`;

    setAbriendo(true);
    setError(null);
    try {
      const html = await transporteService.getInformeCuentaCobro({
        placa,
        mes,
        anio,
      });
      ventana.document.open();
      ventana.document.write(html);
      ventana.document.close();
    } catch (err) {
      // Si no llegó el documento, la pestaña en blanco no sirve: se cierra
      // y el error queda aquí, en el bloque.
      ventana.close();
      const apiError = err as ApiError;
      setError(
        apiError?.message ?? "No fue posible generar la cuenta de cobro.",
      );
      logDevelopmentError("Error generando la cuenta de cobro:", err);
    } finally {
      setAbriendo(false);
    }
  };

  if (opciones.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        No hay vehículos con salidas en este periodo: la cuenta de cobro se
        calcula desde ellas.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap items-end gap-2 px-2 pt-1">
      <label className="flex flex-col gap-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Vehículo
        </span>
        <select
          value={placa}
          onChange={(e) => setPlaca(e.target.value)}
          className={SELECT_CLASES}
          aria-label="Vehículo de la cuenta de cobro"
        >
          <option value="">Seleccione una placa</option>
          {opciones.map((vehiculo) => (
            <option key={vehiculo.placa} value={vehiculo.placa}>
              {vehiculo.placa} — {vehiculo.propietario}
            </option>
          ))}
        </select>
      </label>

      <button
        type="button"
        onClick={() => void abrir()}
        disabled={!placa || abriendo}
        className={`${BOTON_CLASES} disabled:cursor-not-allowed disabled:opacity-60`}
        title={
          "Documento imprimible del alquiler del vehículo en el periodo. " +
          "El importe y el pagador se calculan en el servidor (F5-1)."
        }
      >
        {abriendo ? "Generando…" : "Abrir cuenta de cobro"}
      </button>

      {error && (
        <span className="pb-2 text-xs text-error-500" role="alert">
          {error}
        </span>
      )}
    </div>
  );
};
