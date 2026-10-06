// src/utils/permission.ts
import { AuthUser } from "@/services/auth.service";

/**
 * Normaliza cadenas removiendo tildes, caracteres especiales,
 * espacios innecesarios y convirtiendo a mayúsculas.
 */
const normalizeText = (str?: string | null): string => {
  if (!str) return "";
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toUpperCase();
};

/**
 * Evalúa si un usuario tiene permiso para acceder al módulo de generación
 * de certificados laborales.
 *
 * Condiciones:
 * 1. Es superusuario (`is_superuser: true`).
 * 2. O pertenece al área 'GESTION HUMANA' Y a la carpeta 'GESTION HUMANA'.
 */
export const hasCertificadosPermission = (
  user: AuthUser | null | undefined,
): boolean => {
  if (!user) return false;
  if (user.is_superuser) return true;

  const area = normalizeText(user.area);
  const carpeta = normalizeText(user.carpeta);

  const isGestionHumanaArea =
    area.includes("GESTION HUMANA") ||
    area.includes("GESTION DE PERSONAL") ||
    area.includes("RECURSOS HUMANOS") ||
    area.includes("RRHH");

  const isGestionHumanaCarpeta =
    carpeta.includes("GESTION HUMANA") ||
    carpeta.includes("GESTION DE PERSONAL") ||
    carpeta.includes("RECURSOS HUMANOS") ||
    carpeta.includes("RRHH");

  // Cumple la condición si pertenece estrictamente a AMBAS (área Y carpeta de Gestión Humana)
  return isGestionHumanaArea && isGestionHumanaCarpeta;
};

/**
 * Evalúa si un usuario tiene permiso para gestionar/modificar la firma
 * del certificado laboral.
 *
 * Condiciones:
 * 1. Es superusuario (`is_superuser: true`).
 * 2. O pertenece al área o carpeta 'PROGRAMACION' o 'ADMIN'.
 */
export const hasFirmaConfigPermission = (
  user: AuthUser | null | undefined,
): boolean => {
  if (!user) return false;
  if (user.is_superuser) return true;

  const area = normalizeText(user.area);
  const carpeta = normalizeText(user.carpeta);

  return (
    area.includes("PROGRAMACION") ||
    area.includes("ADMIN") ||
    carpeta.includes("PROGRAMACION") ||
    carpeta.includes("ADMIN")
  );
};

/**
 * Áreas/carpetas que pueden entrar a **Gestión SMU** (supervisión de los
 * formularios): el equipo de programación y el equipo SMU.
 *
 * Los valores son los que existen en el directorio (`Empleado.area` /
 * `Empleado.carpeta`): `PROGRAMACION` y `SMU` aparecen como carpeta y
 * `PROGRAMACION` también como área. Se comparan sin tildes ni mayúsculas,
 * así que si el directorio incorpora un nombre nuevo, se agrega aquí.
 */
const GESTION_SMU_CLAVES = ["PROGRAMACION", "SMU"];

/**
 * Evalúa si un usuario puede ver el módulo de gestión y supervisión SMU
 * (`/smu/gestion_smu`).
 *
 * Condiciones:
 * 1. Es superusuario.
 * 2. O su área **o** su carpeta contiene alguna clave de `GESTION_SMU_CLAVES`
 *    (programadores y equipo SMU).
 */
export const hasGestionSmuPermission = (
  user: AuthUser | null | undefined,
): boolean => {
  if (!user) return false;
  if (user.is_superuser) return true;

  const area = normalizeText(user.area);
  const carpeta = normalizeText(user.carpeta);

  return GESTION_SMU_CLAVES.some(
    (clave) => area.includes(clave) || carpeta.includes(clave),
  );
};
