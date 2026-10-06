import React from "react";
import SectionHeader from "../../common/SectionHeader";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import { FileCheck2, PenTool, ShieldCheck } from "lucide-react";
import { FormCapexTipologia1Data } from "./types";

interface Paso8RecomendacionesCierreProps {
  formData: FormCapexTipologia1Data;
  updateField: <K extends keyof FormCapexTipologia1Data>(
    field: K,
    value: FormCapexTipologia1Data[K],
  ) => void;
}

export const Paso8RecomendacionesCierre: React.FC<Paso8RecomendacionesCierreProps> = ({
  formData,
  updateField,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="7. RECOMENDACIONES DE LA ACTIVIDAD Y FIRMAS DE CIERRE"
        description="Recomendaciones generales, observaciones de entrega y firma de conformidad de la intervención SPT."
      />

      {/* 7. RECOMENDACIONES DE LA ACTIVIDAD */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <div className="mb-2 flex items-center gap-2 text-brand-600 dark:text-brand-400">
          <FileCheck2 className="h-4 w-4" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
            7. RECOMENDACIONES DE LA ACTIVIDAD
          </h4>
        </div>
        <TextArea
          rows={4}
          placeholder="Escriba las recomendaciones de mantenimiento futuro, precauciones de seguridad o inspecciones periódicas..."
          value={formData.recomendaciones_finales}
          onChange={(e) => updateField("recomendaciones_finales", e.target.value)}
        />
      </div>

      {/* Firmas de Cierre */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {/* Responsable técnico que entrega */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
          <div className="mb-4 flex items-center gap-2 text-brand-600 dark:text-brand-400">
            <PenTool className="h-4 w-4" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
              Responsable Técnico que Entrega
            </h4>
          </div>

          <div className="space-y-3">
            <div>
              <Label>Nombre Completo</Label>
              <Input
                placeholder="Nombre del técnico ejecutor"
                value={formData.responsable_entrega_nombre}
                onChange={(e) => updateField("responsable_entrega_nombre", e.target.value)}
              />
            </div>

            <div>
              <Label>Cédula de Ciudadanía</Label>
              <Input
                placeholder="Número de cédula"
                value={formData.responsable_entrega_cedula}
                onChange={(e) => updateField("responsable_entrega_cedula", e.target.value)}
              />
            </div>

            <div>
              <Label>Cargo / Rol</Label>
              <Input
                placeholder="Cargo técnico"
                value={formData.responsable_entrega_cargo}
                onChange={(e) => updateField("responsable_entrega_cargo", e.target.value)}
              />
            </div>

            <div>
              <Label>Fecha de Entrega</Label>
              <Input
                type="date"
                value={formData.responsable_entrega_fecha}
                onChange={(e) => updateField("responsable_entrega_fecha", e.target.value)}
              />
            </div>

            <div>
              <Label>Firma Digital / Observación</Label>
              <Input
                placeholder="Firma del técnico ejecutor"
                value={formData.responsable_entrega_firma}
                onChange={(e) => updateField("responsable_entrega_firma", e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Coordinador Aliado que Recibe */}
        <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
          <div className="mb-4 flex items-center gap-2 text-brand-600 dark:text-brand-400">
            <ShieldCheck className="h-4 w-4" />
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300">
              Aprobación / Coordinador Aliado que Recibe
            </h4>
          </div>

          <div className="space-y-3">
            <div>
              <Label>Aprobado Por (Nombre)</Label>
              <Input
                placeholder="Nombre del coordinador / interventor"
                value={formData.aprobado_nombre}
                onChange={(e) => updateField("aprobado_nombre", e.target.value)}
              />
            </div>

            <div>
              <Label>Cédula de Ciudadanía</Label>
              <Input
                placeholder="Número de cédula"
                value={formData.aprobado_cedula}
                onChange={(e) => updateField("aprobado_cedula", e.target.value)}
              />
            </div>

            <div>
              <Label>Cargo / Rol</Label>
              <Input
                placeholder="Coordinador / Interventor Aliado"
                value={formData.aprobado_cargo}
                onChange={(e) => updateField("aprobado_cargo", e.target.value)}
              />
            </div>

            <div>
              <Label>Fecha de Aprobación</Label>
              <Input
                type="date"
                value={formData.aprobado_fecha}
                onChange={(e) => updateField("aprobado_fecha", e.target.value)}
              />
            </div>

            <div>
              <Label>Firma de Aprobación</Label>
              <Input
                placeholder="Firma de quien aprueba"
                value={formData.aprobado_firma}
                onChange={(e) => updateField("aprobado_firma", e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
        <Label>Observaciones Finales de Cierre</Label>
        <TextArea
          rows={3}
          placeholder="Comentarios finales de la entrega del mantenimiento correctivo de SPT..."
          value={formData.observaciones_cierre}
          onChange={(e) => updateField("observaciones_cierre", e.target.value)}
        />
      </div>
    </div>
  );
};
