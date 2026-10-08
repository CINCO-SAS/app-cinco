export interface ChangePasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

/**
 * Reglas del checklist en tiempo real. Deben mantenerse en espejo con
 * `AUTH_PASSWORD_VALIDATORS` (backend/config/settings.py) — en particular con
 * `ComplexityPasswordValidator` — para que el usuario vea exactamente lo que
 * va a exigir el backend.
 */
export interface PasswordValidationState {
  hasMinLength: boolean;
  hasUpperCase: boolean;
  hasLowerCase: boolean;
  hasNumber: boolean;
  hasSpecial: boolean;
  passwordsMatch: boolean;
  isNotCurrent: boolean;
}

export interface ChangePasswordResult {
  success: boolean;
  message: string;
}
