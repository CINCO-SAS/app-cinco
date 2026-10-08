import api from "@/lib/api";
import { classifyError } from "@/lib/errorHandler";
import {
  ChangePasswordFormData,
  ChangePasswordResult,
  PasswordValidationState,
} from "../types/configuracion.types";

/**
 * Longitud mínima exigida por el backend (`MinimumLengthValidator`).
 * Debe mantenerse en settings.AUTH_PASSWORD_VALIDATORS.
 */
export const PASSWORD_MIN_LENGTH = 8;

export const validatePasswordRules = (
  data: ChangePasswordFormData
): PasswordValidationState => {
  const { currentPassword, newPassword, confirmPassword } = data;
  return {
    hasMinLength: newPassword.length >= PASSWORD_MIN_LENGTH,
    hasUpperCase: /[A-Z]/.test(newPassword),
    hasLowerCase: /[a-z]/.test(newPassword),
    hasNumber: /[0-9]/.test(newPassword),
    hasSpecial: /[^A-Za-z0-9]/.test(newPassword),
    passwordsMatch: newPassword.length > 0 && newPassword === confirmPassword,
    isNotCurrent: Boolean(
      newPassword && currentPassword && newPassword !== currentPassword
    ),
  };
};

export const updatePasswordService = async (
  data: ChangePasswordFormData
): Promise<ChangePasswordResult> => {
  const payload = {
    current_password: data.currentPassword,
    new_password: data.newPassword,
    confirm_new_password: data.confirmPassword,
  };

  try {
    const response = await api.post<ChangePasswordResult>(
      "/auth/change-password/",
      payload
    );

    return {
      success: response.data?.success ?? true,
      message:
        response.data?.message || "Contraseña actualizada exitosamente.",
    };
  } catch (error) {
    // `api.ts` ya rechaza con errores clasificados; `classifyError` los deja
    // pasar tal cual y normaliza cualquier otro fallo (red, timeout, etc.).
    throw classifyError(error);
  }
};
