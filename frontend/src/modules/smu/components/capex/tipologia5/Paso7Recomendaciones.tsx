import React from "react";
import SectionHeader from "../../common/SectionHeader";
import TextArea from "@/components/form/input/TextArea";
import { FileCheck2 } from "lucide-react";
import { FormCapexTipologia5Data } from "./types";

interface Paso7RecomendacionesProps {
  formData: FormCapexTipologia5Data;
  updateField: <K extends keyof FormCapexTipologia5Data>(
    field: K,
    value: FormCapexTipologia5Data[K],
  ) => void;
}

export const Paso7Recomendaciones: React.FC<Paso7RecomendacionesProps> = ({
  formData,
  updateField,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="6. RECOMENDACIONES DE LA ACTIVIDAD"
        description="Recomendaciones de mantenimiento futuro, precauciones de seguridad, observaciones técnicas y condiciones de entrega de la intervención."
      />

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-3 flex items-center gap-2">
          <FileCheck2 className="h-4 w-4 text-brand-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            Recomendaciones del Aliado
          </span>
        </div>
        <TextArea
          rows={6}
          placeholder="Escriba las recomendaciones de mantenimiento futuro, precauciones de seguridad o inspecciones periódicas..."
          value={formData.recomendaciones_finales}
          onChange={(e) => updateField("recomendaciones_finales", e.target.value)}
        />
      </div>
    </div>
  );
};
