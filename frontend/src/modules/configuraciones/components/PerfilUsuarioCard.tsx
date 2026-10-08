"use client";

import React from "react";
import { useAuthStore } from "@/store/auth.store";
import { getAvatarUrl } from "@/utils/avatar";
import {
  IdCard,
  Mail,
  Building2,
} from "lucide-react";

export const PerfilUsuarioCard: React.FC = () => {
  const user = useAuthStore((state) => state.user);

  const fullName = [user?.nombre, user?.apellido].filter(Boolean).join(" ") || "Usuario del Sistema";
  const initials = (user?.nombre?.[0] || user?.username?.[0] || "U").toUpperCase() +
    (user?.apellido?.[0] || "").toUpperCase();
  const avatarUrl = getAvatarUrl(user?.foto);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all duration-200 dark:border-gray-800 dark:bg-gray-900">
      {/* Header del Perfil */}
      <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-start sm:text-left">
        {/* Avatar: foto real o iniciales como fallback */}
        <div className="relative flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-tr from-brand-600 to-brand-400 text-2xl font-bold text-white shadow-md shadow-brand-500/20 ring-4 ring-white dark:ring-gray-900 overflow-hidden">
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={fullName}
              className="h-full w-full object-cover"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
                (e.currentTarget.nextSibling as HTMLElement | null)?.removeAttribute("hidden");
              }}
            />
          ) : null}
          <span hidden={!!avatarUrl}>{initials}</span>
        </div>

        {/* Info básica de cabecera */}
        <div className="flex-1">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            {fullName}
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {user?.email || "Sin correo electrónico configurado"}
          </p>
        </div>
      </div>

      <div className="my-6 border-t border-gray-100 dark:border-gray-800" />

      {/* Detalle de Datos Básicos */}
      <h4 className="mb-4 text-xs font-bold tracking-wider text-gray-400 uppercase dark:text-gray-500">
        Información Básica del Usuario
      </h4>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-3.5 dark:border-gray-800 dark:bg-gray-800/40">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <IdCard className="h-4 w-4 text-brand-500" />
            <span>Documento / Cédula</span>
          </div>
          <p className="mt-1 font-semibold text-gray-900 dark:text-white">
            {user?.username || "No asignado"}
          </p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-3.5 dark:border-gray-800 dark:bg-gray-800/40">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <Mail className="h-4 w-4 text-brand-500" />
            <span>Correo Institucional</span>
          </div>
          <p className="mt-1 font-semibold text-gray-900 dark:text-white truncate">
            {user?.email || "Sin registrar"}
          </p>
        </div>

        <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-3.5 dark:border-gray-800 dark:bg-gray-800/40">
          <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <Building2 className="h-4 w-4 text-brand-500" />
            <span>Área / Sede</span>
          </div>
          <p className="mt-1 font-semibold text-gray-900 dark:text-white">
            {user?.area || "Operaciones / General"}
          </p>
        </div>

      </div>
    </div>
  );
};
