import React from "react";
import SectionHeader from "../../common/SectionHeader";
import AddItemButton from "../../common/AddItemButton";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import { Trash2, Calculator, Sparkles, RefreshCw } from "lucide-react";
import { FilaMedidaSPT, FormCapexTipologia1Data } from "./types";
import { SPTResultChart } from "./SPTResultChart";

interface Paso5ResultadosSPTProps {
  formData: FormCapexTipologia1Data;
  updateField: <K extends keyof FormCapexTipologia1Data>(
    field: K,
    value: FormCapexTipologia1Data[K],
  ) => void;
  onAddFilaSPT: () => void;
  onRemoveFilaSPT: (id: string) => void;
  onUpdateFilaSPT: (id: string, field: keyof FilaMedidaSPT, value: string) => void;
  onPhotoUpload: (field: keyof FormCapexTipologia1Data, file: File) => void;
  onPhotoRemove: (field: keyof FormCapexTipologia1Data) => void;
  onFotoDescripcion?: (valor: string) => void;
}

const PRESET_DISTANCIAS = ["5", "10", "15", "20", "25"];

export const Paso5ResultadosSPT: React.FC<Paso5ResultadosSPTProps> = ({
  formData,
  updateField,
  onAddFilaSPT,
  onRemoveFilaSPT,
  onUpdateFilaSPT,
  onPhotoUpload,
  onPhotoRemove,
  onFotoDescripcion,
}) => {
  const handleCargarPreset = () => {
    const filasPreset: FilaMedidaSPT[] = PRESET_DISTANCIAS.map((dist, idx) => {
      const existing = formData.filas_spt[idx];
      const medida = existing?.medida_ohmio || "";
      let resistividad = "";
      if (Number(dist) > 0 && Number(medida) > 0) {
        resistividad = (2 * Math.PI * Number(dist) * Number(medida)).toFixed(6);
      }
      return {
        id: existing?.id || `spt-${Date.now()}-${idx + 1}`,
        distancia: dist,
        medida_ohmio: medida,
        resistividad,
      };
    });
    updateField("filas_spt", filasPreset);
  };

  return (
    <div className="space-y-6">
      <SectionHeader
        title="4. RESULTADOS DE REFORMA SPT"
        description="Naturaleza del terreno, tabla de medidas de resistividad post-reforma y curva de comportamiento gráfico."
      />

      {/* 4.1 TABLA NATURALEZA DEL TERRENO */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-3">
          <Label className="font-semibold">4.1. Naturaleza del Terreno</Label>
        </div>

        <div className="grid grid-cols-1 items-start gap-6 md:grid-cols-12">
          <div className="space-y-2 md:col-span-7 lg:col-span-8">
            <Label>Descripción de la Naturaleza del Terreno</Label>
            <TextArea
              rows={5}
              placeholder="Descripción de la composición del suelo..."
              value={formData.spt_naturaleza_terreno_desc}
              onChange={(e) => updateField("spt_naturaleza_terreno_desc", e.target.value)}
            />
            <p className="text-[11px] text-gray-400 dark:text-gray-500">
              Indique tipo de suelo, presencia de roca, nivel freático o tratamientos aplicados.
            </p>
          </div>

          <div className="w-full md:col-span-5 lg:col-span-4">
            <Label>Registro Fotográfico del Terreno</Label>
            <FotoSlotWithDescripcion
              index={1}
              titulo="Muestra / Naturaleza Terreno"
              inputId="foto-naturaleza-terreno"
              previewUrl={formData.spt_naturaleza_terreno_foto}
              onUpload={(file) => file && onPhotoUpload("spt_naturaleza_terreno_foto", file)}
              onRemove={() => onPhotoRemove("spt_naturaleza_terreno_foto")}
              descripcion={
                formData.spt_naturaleza_terreno_foto_descripcion ?? ""
              }
              onDescripcionChange={(valor) => onFotoDescripcion?.(valor)}
              descripcionLabel="Descripción de la foto"
            />
          </div>
        </div>
      </div>

      {/* 4.2 y 4.3 TABLA MEDIDAS DE RESISTIVIDAD Y GRÁFICO EN GRID BALANCEADO */}
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        {/* Columna Izquierda: Tabla interactiva */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5 lg:col-span-7 dark:border-gray-800 dark:bg-white/[0.02]">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 pb-3 dark:border-gray-800">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
              4.2. Medidas de Resistividad (Post-Reforma)
            </h4>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCargarPreset}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-[11px] font-semibold text-gray-700 transition-all hover:bg-gray-100 dark:border-gray-700 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10"
                title="Cargar distancias estándar (5m a 25m)"
              >
                <RefreshCw className="h-3 w-3 text-brand-500" />
                Distancias Estándar (5-25m)
              </button>

              <AddItemButton label="Añadir Fila" onClick={onAddFilaSPT} />
            </div>
          </div>

          <div className="mb-3 flex items-center gap-2 rounded-xl bg-brand-50/50 p-2.5 text-xs text-brand-700 dark:bg-brand-500/10 dark:text-brand-300">
            <Calculator className="h-4 w-4 shrink-0 text-brand-600 dark:text-brand-400" />
            <span>
              <strong>Fórmula Wenner:</strong> ρ = 2 · π · a · R (cálculo automático instantáneo)
            </span>
          </div>

          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-transparent">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-gray-200 bg-gray-50/80 text-[11px] font-semibold uppercase tracking-wider text-gray-600 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-400">
                <tr>
                  <th className="py-2.5 px-3">Distancia (m)</th>
                  <th className="py-2.5 px-3">Medida (Ω)</th>
                  <th className="py-2.5 px-3">Resistividad (Ω·m)</th>
                  <th className="py-2.5 px-2 text-center w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {formData.filas_spt.map((fila, idx) => (
                  <tr
                    key={fila.id}
                    className="transition-colors hover:bg-gray-50/50 dark:hover:bg-white/[0.01]"
                  >
                    {/* Distancia */}
                    <td className="py-2 px-3">
                      <div className="relative">
                        <Input
                          type="number"
                          min="0"
                          step="0.1"
                          value={fila.distancia}
                          onChange={(e) => onUpdateFilaSPT(fila.id, "distancia", e.target.value)}
                        />
                      </div>
                    </td>

                    {/* Medida en Ohmios */}
                    <td className="py-2 px-3">
                      <div className="relative">
                        <Input
                          type="number"
                          min="0"
                          step="0.0001"
                          value={fila.medida_ohmio}
                          onChange={(e) => onUpdateFilaSPT(fila.id, "medida_ohmio", e.target.value)}
                        />
                      </div>
                    </td>

                    {/* Resistividad Calculada */}
                    <td className="py-2 px-3">
                      <div className="flex h-8 items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-2.5 font-mono text-xs font-semibold text-gray-800 dark:border-gray-800 dark:bg-white/[0.02] dark:text-white/90">
                        <span>{fila.resistividad ? Number(fila.resistividad).toFixed(4) : "—"}</span>
                        <span className="text-[10px] font-normal text-gray-400">Ω·m</span>
                      </div>
                    </td>

                    {/* Acción Eliminar */}
                    <td className="py-2 px-2 text-center">
                      {formData.filas_spt.length > 1 && (
                        <button
                          type="button"
                          onClick={() => onRemoveFilaSPT(fila.id)}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition-all hover:bg-error-50 hover:text-error-500 dark:hover:bg-error-500/10"
                          title="Eliminar fila"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Columna Derecha: Gráfico Curva SPT */}
        <div className="lg:col-span-5">
          <SPTResultChart filas={formData.filas_spt} />
        </div>
      </div>

      {/* 4.4 RECOMENDACIÓN ALIADO */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-2 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-brand-500" />
          <Label className="mb-0 font-semibold">4.4. Recomendación Aliado (Resultados de Reforma SPT)</Label>
        </div>
        <TextArea
          rows={3}
          placeholder="Escriba las conclusiones técnicas sobre la resistividad obtenida, equipotencialización y estado del sistema de puesta a tierra..."
          value={formData.spt_recomendacion_aliado}
          onChange={(e) => updateField("spt_recomendacion_aliado", e.target.value)}
        />
      </div>
    </div>
  );
};
