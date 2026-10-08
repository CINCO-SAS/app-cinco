"use client";

import React from "react";
import { Settings } from "lucide-react";
import { PerfilUsuarioCard } from "./PerfilUsuarioCard";
import { CambioPasswordCard } from "./CambioPasswordCard";

export const ConfiguracionesView: React.FC = () => {
  return (
    <div className="space-y-6 pb-12">
      {/* Header del Módulo */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="flex items-center gap-3.5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-brand-600 to-brand-400 text-white shadow-md shadow-brand-500/20">
            <Settings className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Configuraciones de la Cuenta
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Consulta tus datos de usuario y gestiona la seguridad y credenciales de acceso.
            </p>
          </div>
        </div>
      </div>

      {/* Grid con las 2 secciones principales */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Columna Izquierda: Datos del Usuario */}
        <div>
          <PerfilUsuarioCard />
        </div>

        {/* Columna Derecha: Cambio y Validación de Contraseña */}
        <div>
          <CambioPasswordCard />
        </div>
      </div>
    </div>
  );
};
