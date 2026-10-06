"use client";

import React, { useState, useCallback } from "react";
import SelectorTipoActividad from "./SelectorTipoActividad";
import FormPreventivos from "./FormPreventivos";
import FormCorrectivosCapex from "./FormCorrectivosCapex";
import FormEmergenciaCorrectivos from "./FormEmergenciaCorrectivos";
import type {
  GrupoActividad,
  CategoriaActividad,
  TipoFormulario,
  SmuFormState,
} from "../types/smu.types";

const SmuDashboard: React.FC = () => {
  const [formState, setFormState] = useState<SmuFormState>({
    grupo: null,
    categoria: null,
    tipo_formulario: null,
  });

  // Al cambiar el grupo (primer radio), se limpia categoria y tipo_formulario.
  // Para preventivos y correctivos_capex, la categoria coincide con el grupo.
  // Para emergencia_correctivos, la categoria la elige el sub-radio.
  const handleGrupoChange = useCallback((grupo: GrupoActividad) => {
    let categoria: CategoriaActividad | null = null;

    if (grupo === "preventivos") categoria = "preventivos";
    else if (grupo === "correctivos_capex") categoria = "correctivos_capex";
    // "emergencia_correctivos" → la categoria la define el sub-radio

    setFormState({ grupo, categoria, tipo_formulario: null });
  }, []);

  const handleCategoriaChange = useCallback((categoria: CategoriaActividad) => {
    setFormState((prev) => ({ ...prev, categoria, tipo_formulario: null }));
  }, []);

  const handleTipoFormularioChange = useCallback((tipo_formulario: TipoFormulario) => {
    setFormState((prev) => ({ ...prev, tipo_formulario }));
  }, []);

  const renderFormulario = () => {
    switch (formState.grupo) {
      case "preventivos":
        return (
          <FormPreventivos
            tipoFormulario={formState.tipo_formulario}
            onChangeTipoFormulario={handleTipoFormularioChange}
          />
        );
      case "correctivos_capex":
        return (
          <FormCorrectivosCapex
            tipoFormulario={formState.tipo_formulario}
            onChangeTipoFormulario={handleTipoFormularioChange}
          />
        );
      case "emergencia_correctivos":
        return (
          <FormEmergenciaCorrectivos
            categoria={formState.categoria}
            onChangeCategoria={handleCategoriaChange}
            tipoFormulario={formState.tipo_formulario}
            onChangeTipoFormulario={handleTipoFormularioChange}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Encabezado centrado */}
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-8 text-center dark:border-gray-800 dark:bg-white/3">
        <h3 className="text-xl font-semibold text-gray-800 dark:text-white/90">
          Registro de Actividad SMU
        </h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Selecciona el tipo de actividad para continuar con el registro
        </p>
      </div>

      {/* Selector principal */}
      <div className="rounded-2xl border border-gray-200 bg-white px-6 py-6 dark:border-gray-800 dark:bg-white/3">
        <SelectorTipoActividad
          value={formState.grupo}
          onChange={handleGrupoChange}
        />
      </div>

      {/* Formulario condicional */}
      {formState.grupo && (
        <div className="transition-all duration-300">
          {renderFormulario()}
        </div>
      )}
    </div>
  );
};

export default SmuDashboard;
