import React from "react";
import SectionHeader from "../../common/SectionHeader";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import EmployeeSearchInput from "@/components/form/EmployeeSearchInput";
import { FormCapexTipologia1Data } from "./types";

interface Paso1GeneralProps {
  formData: FormCapexTipologia1Data;
  updateField: <K extends keyof FormCapexTipologia1Data>(
    field: K,
    value: FormCapexTipologia1Data[K],
  ) => void;
}

export const Paso1General: React.FC<Paso1GeneralProps> = ({
  formData,
  updateField,
}) => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="Información General"
        description="Datos de la estación base, orden de trabajo, contratista y responsables de la actividad."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
        <div>
          <Label>Nombre Estación Base</Label>
          <Input
            placeholder="Nombre de la estación"
            value={formData.nombre_estacion}
            onChange={(e) => updateField("nombre_estacion", e.target.value)}
          />
        </div>

        <div>
          <Label>Orden de Trabajo (OT)</Label>
          <Input
            placeholder="Código OT"
            value={formData.ot}
            onChange={(e) => updateField("ot", e.target.value)}
          />
        </div>

        <div>
          <Label>Tipo Estación Base</Label>
          <Input
            placeholder="Tipo de estación"
            value={formData.tipo_estacion}
            onChange={(e) => updateField("tipo_estacion", e.target.value)}
          />
        </div>

        <div>
          <Label>Fecha Inicio Actividad</Label>
          <Input
            type="datetime-local"
            value={formData.fecha_inicio}
            onChange={(e) => updateField("fecha_inicio", e.target.value)}
          />
        </div>

        <div>
          <Label>Fecha Final Actividad</Label>
          <Input
            type="datetime-local"
            value={formData.fecha_fin}
            onChange={(e) => updateField("fecha_fin", e.target.value)}
          />
        </div>

        <div>
          <Label>Nombre Site Owner</Label>
          <Input
            placeholder="Site owner / Operador"
            value={formData.site_owner}
            onChange={(e) => updateField("site_owner", e.target.value)}
          />
        </div>

        <div>
          <Label>Empresa / Aliado Ejecutor</Label>
          <Input
            placeholder="Empresa quien ejecuta"
            value={formData.empresa}
            onChange={(e) => updateField("empresa", e.target.value)}
          />
        </div>

        <div>
          <Label>Coordinador Aliado</Label>
          <Input
            placeholder="Nombre del coordinador"
            value={formData.coordinador_aliado}
            onChange={(e) => updateField("coordinador_aliado", e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 pt-2 sm:grid-cols-2">
        <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/2">
          <EmployeeSearchInput
            label="Nombre de quien ejecuta la actividad *"
            placeholder="Buscar por cédula o nombre..."
            value={formData.responsable_ejecuta}
            onChange={(emp) => updateField("responsable_ejecuta", emp)}
            name="responsable_ejecuta"
            hint="Técnico principal ejecutor de la reforma en sitio"
            required
          />
        </div>
      </div>
    </div>
  );
};
