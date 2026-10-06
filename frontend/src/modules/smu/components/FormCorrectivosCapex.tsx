"use client";

import React from "react";
import RadioCardGroup from "./RadioCardGroup";
import FormCapexTipologia1Slider from "./capex/FormCapexTipologia1Slider";
import FormCapexTipologia3Slider from "./capex/FormCapexTipologia3Slider";
import FormCapexTipologia5Slider from "./capex/FormCapexTipologia5Slider";
import type { TipoFormulario } from "../types/smu.types";

interface FormCorrectivosCapexProps {
  tipoFormulario: TipoFormulario | null;
  onChangeTipoFormulario: (v: TipoFormulario) => void;
}

const opcionesSubtipo = [
  {
    value: "tipologia1" as TipoFormulario,
    label: "Tipología 1",
    descripcion: "Reforma SPT / Pararrayos",
  },
  {
    value: "tipologia3" as TipoFormulario,
    label: "Tipología 3",
    descripcion: "Climatización",
  },
  {
    value: "tipologia5" as TipoFormulario,
    label: "Tipología 5",
    descripcion: "Subestaciones eléctricas",
  },
];

/**
 * Registro de formularios CAPEX por nombre de tipología.
 * Para habilitar una nueva tipología: crear el slider en ./capex/
 * y registrarlo aquí con su nombre (tipologia1, tipologia3, tipologia5...).
 */
const FORMULARIOS_TIPOLOGIA: Partial<Record<TipoFormulario, React.FC>> = {
  tipologia1: FormCapexTipologia1Slider,
  tipologia3: FormCapexTipologia3Slider,
  tipologia5: FormCapexTipologia5Slider,
};

const FormCorrectivosCapex: React.FC<FormCorrectivosCapexProps> = ({
  tipoFormulario,
  onChangeTipoFormulario,
}) => {
  const capexValidos: TipoFormulario[] = [
    "tipologia1",
    "tipologia3",
    "tipologia5",
  ];
  const valorActual = capexValidos.includes(tipoFormulario as TipoFormulario)
    ? (tipoFormulario as TipoFormulario)
    : null;
  const FormularioTipologia = valorActual
    ? FORMULARIOS_TIPOLOGIA[valorActual]
    : undefined;

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-6 dark:border-gray-800 dark:bg-white/3">
        <RadioCardGroup
          name="tipo_formulario_capex"
          label="Tipología CAPEX"
          options={opcionesSubtipo}
          value={valorActual}
          onChange={onChangeTipoFormulario}
          cols={3}
        />
      </div>

      {/* Formulario de la tipología seleccionada (si está registrado) */}
      {FormularioTipologia && <FormularioTipologia />}

      {/* Tipología seleccionada aún no registrada en FORMULARIOS_TIPOLOGIA */}
      {valorActual && !FormularioTipologia && (
        <div className="rounded-2xl border border-gray-200 bg-white px-6 py-5 transition-all duration-300 dark:border-gray-800 dark:bg-white/3">
          <p className="text-sm text-gray-400 italic dark:text-gray-500">
            Formulario{" "}
            <span className="font-medium text-gray-600 dark:text-gray-300">
              {opcionesSubtipo.find((o) => o.value === valorActual)?.label}
            </span>{" "}
            — en construcción.
          </p>
        </div>
      )}
    </div>
  );
};

export default FormCorrectivosCapex;
