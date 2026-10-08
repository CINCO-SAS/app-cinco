"use client";

import React, { useState } from "react";
import {
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ShieldCheck,
  KeyRound,
  Loader2,
} from "lucide-react";
import {
  ChangePasswordFormData,
  PasswordValidationState,
} from "../types/configuracion.types";
import {
  PASSWORD_MIN_LENGTH,
  updatePasswordService,
  validatePasswordRules,
} from "../services/configuracion.service";
import { classifyError, getToastErrorMessage } from "@/lib/errorHandler";

export const CambioPasswordCard: React.FC = () => {
  const [formData, setFormData] = useState<ChangePasswordFormData>({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const validations: PasswordValidationState = validatePasswordRules(formData);

  const isFormValid =
    formData.currentPassword.trim().length > 0 &&
    validations.hasMinLength &&
    validations.hasUpperCase &&
    validations.hasLowerCase &&
    validations.hasNumber &&
    validations.hasSpecial &&
    validations.passwordsMatch &&
    validations.isNotCurrent;

  const handleChange = (field: keyof ChangePasswordFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errorMsg) setErrorMsg(null);
    if (successMsg) setSuccessMsg(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid || loading) return;

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const result = await updatePasswordService(formData);
      setSuccessMsg(result.message);
      // Limpiar formulario tras éxito
      setFormData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    } catch (err: unknown) {
      setErrorMsg(
        getToastErrorMessage(
          classifyError(err),
          "Error al actualizar la contraseña"
        )
      );
    } finally {
      setLoading(false);
    }
  };

  /** Item del checklist de validaciones en tiempo real. */
  const requirement = (
    key: string,
    isValid: boolean,
    label: string,
    pendingLabel?: string
  ) => (
    <div key={key} className="flex items-center gap-1.5">
      {isValid ? (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
      ) : (
        <XCircle className="h-3.5 w-3.5 shrink-0 text-gray-400" />
      )}
      <span
        className={
          isValid
            ? "text-emerald-700 dark:text-emerald-400"
            : "text-gray-500 dark:text-gray-400"
        }
      >
        {!isValid && pendingLabel ? pendingLabel : label}
      </span>
    </div>
  );

  const toggleButton = (
    visible: boolean,
    onToggle: () => void,
    fieldLabel: string
  ) => (
    <button
      type="button"
      onClick={onToggle}
      aria-label={`${visible ? "Ocultar" : "Mostrar"} ${fieldLabel}`}
      className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 dark:hover:text-gray-200"
    >
      {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
    </button>
  );

  const inputClasses =
    "w-full rounded-xl border border-gray-300 bg-white py-2.5 pr-10 pl-10 text-sm text-gray-900 placeholder:text-gray-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500";

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all duration-200 dark:border-gray-800 dark:bg-gray-900">
      {/* Encabezado */}
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
          <KeyRound className="h-5 w-5" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            Seguridad y Cambio de Contraseña
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Valida tu contraseña actual y define una nueva clave segura para tu cuenta.
          </p>
        </div>
      </div>

      <div className="my-5 border-t border-gray-100 dark:border-gray-800" />

      {/* Alertas de Notificación */}
      {successMsg && (
        <div
          role="alert"
          className="mb-5 flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50/80 p-4 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300"
        >
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <div className="text-sm">
            <p className="font-semibold">¡Contraseña Actualizada!</p>
            <p className="mt-0.5 text-xs text-emerald-700 dark:text-emerald-300/90">{successMsg}</p>
          </div>
        </div>
      )}

      {errorMsg && (
        <div
          role="alert"
          className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-300"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600 dark:text-rose-400" />
          <div className="text-sm">
            <p className="font-semibold">Error al cambiar contraseña</p>
            <p className="mt-0.5 text-xs text-rose-700 dark:text-rose-300/90">{errorMsg}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Campo 1: Contraseña Actual */}
        <div>
          <label
            htmlFor="current_password"
            className="block text-xs font-semibold text-gray-700 dark:text-gray-300"
          >
            Contraseña Actual <span className="text-rose-500">*</span>
          </label>
          <div className="relative mt-1.5">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-gray-400">
              <Lock className="h-4 w-4" />
            </div>
            <input
              id="current_password"
              name="current_password"
              type={showCurrent ? "text" : "password"}
              value={formData.currentPassword}
              onChange={(e) => handleChange("currentPassword", e.target.value)}
              placeholder="Ingresa tu contraseña actual para validar"
              autoComplete="current-password"
              required
              className={inputClasses}
            />
            {toggleButton(
              showCurrent,
              () => setShowCurrent(!showCurrent),
              "contraseña actual"
            )}
          </div>
        </div>

        {/* Campo 2: Nueva Contraseña */}
        <div>
          <label
            htmlFor="new_password"
            className="block text-xs font-semibold text-gray-700 dark:text-gray-300"
          >
            Nueva Contraseña <span className="text-rose-500">*</span>
          </label>
          <div className="relative mt-1.5">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-gray-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <input
              id="new_password"
              name="new_password"
              type={showNew ? "text" : "password"}
              value={formData.newPassword}
              onChange={(e) => handleChange("newPassword", e.target.value)}
              placeholder="Define tu nueva contraseña segura"
              autoComplete="new-password"
              minLength={PASSWORD_MIN_LENGTH}
              required
              className={inputClasses}
            />
            {toggleButton(
              showNew,
              () => setShowNew(!showNew),
              "nueva contraseña"
            )}
          </div>
        </div>

        {/* Campo 3: Confirmación de Nueva Contraseña */}
        <div>
          <label
            htmlFor="confirm_password"
            className="block text-xs font-semibold text-gray-700 dark:text-gray-300"
          >
            Confirmar Nueva Contraseña <span className="text-rose-500">*</span>
          </label>
          <div className="relative mt-1.5">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-gray-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <input
              id="confirm_password"
              name="confirm_new_password"
              type={showConfirm ? "text" : "password"}
              value={formData.confirmPassword}
              onChange={(e) => handleChange("confirmPassword", e.target.value)}
              placeholder="Vuelve a escribir la nueva contraseña"
              autoComplete="new-password"
              minLength={PASSWORD_MIN_LENGTH}
              required
              className={inputClasses}
            />
            {toggleButton(
              showConfirm,
              () => setShowConfirm(!showConfirm),
              "confirmación de contraseña"
            )}
          </div>
        </div>

        {/* Requisitos y Checklist en Tiempo Real */}
        {formData.newPassword.length > 0 && (
          <div className="rounded-xl border border-gray-100 bg-gray-50 p-3.5 text-xs dark:border-gray-800 dark:bg-gray-800/50">
            <p className="font-semibold text-gray-700 dark:text-gray-300">
              Validaciones de seguridad:
            </p>
            <div className="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {requirement(
                "min-length",
                validations.hasMinLength,
                `Mínimo ${PASSWORD_MIN_LENGTH} caracteres`
              )}
              {requirement(
                "uppercase",
                validations.hasUpperCase,
                "Al menos una mayúscula (A-Z)"
              )}
              {requirement(
                "lowercase",
                validations.hasLowerCase,
                "Al menos una minúscula (a-z)"
              )}
              {requirement(
                "number",
                validations.hasNumber,
                "Al menos un número (0-9)"
              )}
              {requirement(
                "special",
                validations.hasSpecial,
                "Al menos un carácter especial (!@#$%&*)"
              )}
              {requirement(
                "not-current",
                validations.isNotCurrent,
                "Diferente a la actual"
              )}
              <div className="flex items-center gap-1.5 sm:col-span-2">
                {validations.passwordsMatch ? (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 shrink-0 text-gray-400" />
                )}
                <span
                  className={
                    validations.passwordsMatch
                      ? "font-medium text-emerald-700 dark:text-emerald-400"
                      : "text-gray-500 dark:text-gray-400"
                  }
                >
                  {formData.confirmPassword.length > 0 && !validations.passwordsMatch
                    ? "Las contraseñas no coinciden"
                    : "Ambas contraseñas coinciden"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Botón de Enviar */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={!isFormValid || loading}
            className={`flex w-full items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-200 ${
              !isFormValid || loading
                ? "cursor-not-allowed bg-gray-400 opacity-60 dark:bg-gray-700"
                : "bg-brand-600 hover:bg-brand-700 shadow-brand-500/25 active:scale-[0.99]"
            }`}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Validando y actualizando...
              </>
            ) : (
              <>
                <ShieldCheck className="h-4 w-4" />
                Guardar Nueva Contraseña
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
