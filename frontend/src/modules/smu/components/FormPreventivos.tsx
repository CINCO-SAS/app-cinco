"use client";

import React from "react";
import RadioCardGroup from "./RadioCardGroup";
import FormPreventivoAASlider from "./preventivos/FormPreventivoAASlider";
import FormPreventivoPlantaSlider from "./preventivos/FormPreventivoPlantaSlider";
import type { TipoFormulario } from "../types/smu.types";

interface FormPreventivosProps {
  tipoFormulario: TipoFormulario | null;
  onChangeTipoFormulario: (v: TipoFormulario) => void;
}

const opcionesSubtipo = [
  {
    value: "aire_acondicionado" as TipoFormulario,
    label: "Preventivo AA",
    descripcion: "Aire acondicionado",
  },
  {
    value: "planta" as TipoFormulario,
    label: "Mantenimiento General de Planta",
    descripcion: "Planta eléctrica / grupo electrógeno",
  },
];

const FormPreventivos: React.FC<FormPreventivosProps> = ({
  tipoFormulario,
  onChangeTipoFormulario,
}) => {
  return (
    <div className="space-y-6">
      {/* Sub-selector tipo formulario preventivo */}
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-6 dark:border-gray-800 dark:bg-white/3">
        <RadioCardGroup
          name="tipo_formulario_preventivo"
          label="Tipo de preventivo"
          options={opcionesSubtipo}
          value={
            tipoFormulario === "aire_acondicionado" ||
            tipoFormulario === "planta"
              ? tipoFormulario
              : null
          }
          onChange={onChangeTipoFormulario}
          cols={2}
        />
      </div>

      {/* Formulario tipo Slider / Wizard para Preventivo AA */}
      {tipoFormulario === "aire_acondicionado" && (
        <div>
          <FormPreventivoAASlider />
        </div>
      )}

      {/* Formulario tipo Slider / Wizard para Preventivo Planta */}
      {tipoFormulario === "planta" && (
        <div>
          <FormPreventivoPlantaSlider />
        </div>
      )}
    </div>
  );
};

export default FormPreventivos;
