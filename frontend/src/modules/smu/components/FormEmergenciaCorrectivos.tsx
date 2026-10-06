"use client";

import React from "react";
import RadioCardGroup from "./RadioCardGroup";
import FormCorrectivoEmergenciaSlider from "./correctivos/FormCorrectivoEmergenciaSlider";
import type { CategoriaActividad, TipoFormulario } from "../types/smu.types";

interface FormEmergenciaCorrectivosProps {
  categoria: CategoriaActividad | null;
  onChangeCategoria: (v: CategoriaActividad) => void;
  tipoFormulario: TipoFormulario | null;
  onChangeTipoFormulario: (v: TipoFormulario) => void;
}

const opcionesCategoria = [
  {
    value: "emergencias" as CategoriaActividad,
    label: "Emergencias",
    descripcion: "Atención de fallas urgentes fuera de programación",
  },
  {
    value: "correctivos" as CategoriaActividad,
    label: "Correctivos",
    descripcion: "Intervención correctiva planificada",
  },
];

const FormEmergenciaCorrectivos: React.FC<FormEmergenciaCorrectivosProps> = ({
  categoria,
  onChangeCategoria,
  tipoFormulario,
  onChangeTipoFormulario,
}) => {
  const categoriaValida =
    categoria === "emergencias" || categoria === "correctivos"
      ? categoria
      : null;

  // Cuando se elige la categoría, se fija el tipo_formulario a "estandar"
  // (único tipo válido para este grupo)
  const handleCategoriaChange = (v: CategoriaActividad) => {
    onChangeCategoria(v);
    if (tipoFormulario !== "estandar") {
      onChangeTipoFormulario("estandar");
    }
  };

  return (
    <div className="space-y-6">
      {/* Sub-selector: Emergencias vs Correctivos */}
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-6 dark:border-gray-800 dark:bg-white/3">
        <RadioCardGroup
          name="categoria_emergencia_correctivo"
          label="Tipo de intervención"
          options={opcionesCategoria}
          value={categoriaValida}
          onChange={handleCategoriaChange}
          cols={2}
        />
      </div>

      {/* Formulario tipo Slider / Wizard para Correctivos y Emergencias */}
      {categoriaValida && (
        <div className="transition-all duration-300">
          <FormCorrectivoEmergenciaSlider categoriaInicial={categoriaValida} />
        </div>
      )}
    </div>
  );
};

export default FormEmergenciaCorrectivos;
