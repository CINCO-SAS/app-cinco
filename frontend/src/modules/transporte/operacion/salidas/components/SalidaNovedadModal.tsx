// src/modules/transporte/operacion/salidas/components/SalidaNovedadModal.tsx
//
// Ítem L · novedad de una salida (B6/B7).
//
// Regla de negocio heredada del legacy y reforzada en el backend: UNA novedad
// por salida. Por eso el modal tiene DOS caras, no un formulario siempre
// visible:
//   · Sin novedad → formulario (tipo ADICIONAL/DESCUENTO + valor + motivo).
//   · Con novedad → resumen de lo que hay + "Quitar novedad".
//
// Esa segunda cara es la mejora sobre el legacy: allí el jefe tenía que
// acordarse de lo que puso para cambiarlo, porque no se veía. Aquí se ve,
// incluido el `descripcion` (por qué se descontó o se adicionó).
//
// El `valor` afecta el cálculo de B10: ADICIONAL suma y DESCUENTO resta.
// `total_a_pagar` lo recalcula el servidor, así que la fila de la tabla se
// actualiza sola al recargar.

"use client";

import { useCallback, useEffect, useState } from "react";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import { Modal } from "@/components/ui/modal";
import Badge from "@/components/ui/badge/Badge";
import {
  BotonDestructivo,
  formatearFechaCorta,
  formatearMoneda,
} from "../salidasView.utils";
import type { Salida, TipoNovedad } from "@/types/transporte.types";

export interface SalidaNovedadModalProps {
  /** `null` → cerrado. */
  salida: Salida | null;
  enviando: boolean;
  errorServidor: string | null;
  onClose: () => void;
  /** Devuelve `true` si la petición falló (el diálogo se queda abierto). */
  onGuardar: (payload: {
    tipo: string;
    valor: string;
    descripcion: string;
  }) => Promise<boolean>;
  /** Devuelve `true` si la petición falló (el diálogo se queda abierto). */
  onEliminar: () => Promise<boolean>;
}

const ETIQUETA_TIPO: Record<TipoNovedad, string> = {
  ADICIONAL: "Adicional",
  DESCUENTO: "Descuento",
};

export const SalidaNovedadModal = ({
  salida,
  enviando,
  errorServidor,
  onClose,
  onGuardar,
  onEliminar,
}: SalidaNovedadModalProps) => {
  const abierto = salida !== null;
  const novedad = salida?.novedad_detalle ?? null;

  const [tipo, setTipo] = useState<TipoNovedad>("DESCUENTO");
  const [valor, setValor] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [errores, setErrores] = useState<{
    valor?: string;
    descripcion?: string;
  }>({});

  useEffect(() => {
    if (abierto) {
      setTipo("DESCUENTO");
      setValor("");
      setDescripcion("");
      setErrores({});
    }
  }, [abierto, salida?.id]);

  const guardar = useCallback(async () => {
    const numero = Number(valor);
    const nuevosErrores: typeof errores = {};

    if (!valor.trim() || Number.isNaN(numero) || numero <= 0) {
      nuevosErrores.valor = "Indica un valor mayor a cero.";
    }
    if (!descripcion.trim()) {
      nuevosErrores.descripcion = "El motivo es obligatorio.";
    }
    setErrores(nuevosErrores);
    if (Object.keys(nuevosErrores).length > 0) return;

    await onGuardar({
      tipo,
      // El backend recibe Decimal; con dos decimales basta (no hay pesos
      // fraccionados en el cálculo de transporte).
      valor: numero.toFixed(2),
      descripcion: descripcion.trim(),
    });
  }, [tipo, valor, descripcion, onGuardar]);

  return (
    <Modal
      isOpen={abierto}
      onClose={() => {
        if (!enviando) onClose();
      }}
      className="max-w-md"
      title="salida-novedad-titulo"
    >
      <div className="px-5 pt-5 pb-1 pr-16">
        <h2
          id="salida-novedad-titulo"
          className="text-base font-semibold text-gray-800 dark:text-white/90"
        >
          Novedad de la salida
        </h2>
      </div>

      <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
        {errorServidor && (
          <Alert variant="error" title="No se pudo guardar" message={errorServidor} />
        )}

        {salida && (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {salida.vehiculo_placa} · {formatearFechaCorta(salida.fecha_salida)}
          </p>
        )}

        {novedad ? (
          // --- Ya tiene novedad: mostrarla y ofrecer quitarla -------------
          <>
            <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-white/[0.03]">
              <div className="flex items-center justify-between">
                <Badge color="warning" size="sm">
                  {ETIQUETA_TIPO[novedad.tipo] ?? novedad.tipo}
                </Badge>
                <span className="text-sm font-semibold tabular-nums text-gray-800 dark:text-white/90">
                  {formatearMoneda(novedad.valor)}
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {novedad.descripcion}
              </p>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Solo puede haber una novedad por salida. Si quieres cambiarla,
              quita esta y registra la nueva.
            </p>
          </>
        ) : (
          // --- Sin novedad: formulario --------------------------------------
          <>
            <div>
              <Label htmlFor="salida-novedad-tipo">
                Tipo <span className="text-error-500">*</span>
              </Label>
              <select
                id="salida-novedad-tipo"
                value={tipo}
                onChange={(e) => setTipo(e.target.value as TipoNovedad)}
                disabled={enviando}
                className="h-11 w-full appearance-none rounded-lg border border-gray-300 bg-transparent px-4 text-sm text-gray-800 outline-none transition focus:border-brand-500 focus:ring-3 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-white/[0.03] dark:text-white/90"
              >
                <option value="DESCUENTO">Descuento (resta)</option>
                <option value="ADICIONAL">Adicional (suma)</option>
              </select>
            </div>

            <div>
              <Label htmlFor="salida-novedad-valor">
                Valor <span className="text-error-500">*</span>
              </Label>
              <Input
                id="salida-novedad-valor"
                type="number"
                min="0"
                step="0.01"
                value={valor}
                onChange={(e) => {
                  setValor(e.target.value);
                  setErrores((prev) => ({ ...prev, valor: undefined }));
                }}
                disabled={enviando}
                error={Boolean(errores.valor)}
                hint={errores.valor ?? undefined}
                placeholder="0"
              />
            </div>

            <div>
              <Label htmlFor="salida-novedad-descripcion">
                Motivo <span className="text-error-500">*</span>
              </Label>
              <Input
                id="salida-novedad-descripcion"
                type="text"
                value={descripcion}
                onChange={(e) => {
                  setDescripcion(e.target.value);
                  setErrores((prev) => ({ ...prev, descripcion: undefined }));
                }}
                disabled={enviando}
                error={Boolean(errores.descripcion)}
                hint={errores.descripcion ?? undefined}
                placeholder="Ej. Espera de 40 minutos en bodega"
              />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
        <Button type="button" variant="outline" onClick={onClose} disabled={enviando}>
          Cancelar
        </Button>
        {novedad ? (
          <BotonDestructivo onClick={() => void onEliminar()} disabled={enviando}>
            {enviando ? "Guardando..." : "Quitar novedad"}
          </BotonDestructivo>
        ) : (
          <Button
            type="button"
            variant="primary"
            onClick={() => void guardar()}
            disabled={enviando}
          >
            {enviando ? "Guardando..." : "Guardar novedad"}
          </Button>
        )}
      </div>
    </Modal>
  );
};
