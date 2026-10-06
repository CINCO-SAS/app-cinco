/**
 * Tipos y utilidades para manejar errores de la API
 */

import { API_BASE_URL } from "@/lib/apiConfig";
import { shouldExposeTechnicalDetails } from "@/lib/environment";
import { ZodError } from "zod";

export enum ApiErrorType {
  VALIDATION = "VALIDATION",
  AUTHENTICATION = "AUTHENTICATION",
  AUTHORIZATION = "AUTHORIZATION",
  NOT_FOUND = "NOT_FOUND",
  CONFLICT = "CONFLICT",
  RATE_LIMIT = "RATE_LIMIT",
  SERVER_ERROR = "SERVER_ERROR",
  NETWORK_ERROR = "NETWORK_ERROR",
  TIMEOUT = "TIMEOUT",
  UNKNOWN = "UNKNOWN",
}

export interface ApiErrorDetail {
  type: ApiErrorType;
  status: number;
  message: string;
  detail?: string;
  errors?: Record<string, string[]>;
  timestamp?: string;
}

export interface ApiError extends Error {
  type: ApiErrorType;
  status: number;
  originalError: any;
  errors?: Record<string, string[]>;
}

const getNetworkErrorMessage = (): string => {
  if (shouldExposeTechnicalDetails()) {
    return `No se pudo conectar con el backend (${API_BASE_URL}). Verifica que Django este corriendo y que la BD/VPN este disponible.`;
  }

  return "No fue posible conectar con el servicio. Intenta nuevamente en unos minutos.";
};

export const containsHtml = (value: unknown): boolean => {
  if (typeof value !== "string") return false;
  const str = value.trim();
  return (
    str.startsWith("<!DOCTYPE") ||
    str.startsWith("<!doctype") ||
    str.startsWith("<html") ||
    str.includes("<body") ||
    /<[a-z][\s\S]*>/i.test(str)
  );
};

const getRawErrorMessage = (error: any): string => {
  if (!error) return "";
  if (typeof error.message === "string") return error.message;
  return String(error);
};

const getFirstNestedMessage = (value: unknown): string | undefined => {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (trimmed && !containsHtml(trimmed)) {
      return trimmed;
    }
    return undefined;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const message = getFirstNestedMessage(item);
      if (message) return message;
    }
    return undefined;
  }

  if (value && typeof value === "object") {
    for (const nestedValue of Object.values(value)) {
      const message = getFirstNestedMessage(nestedValue);
      if (message) return message;
    }
  }

  return undefined;
};

/**
 * Clasifica el tipo de error basado en el estado HTTP y contenido
 */
export function classifyError(error: any): ApiErrorDetail {
  if (
    error &&
    typeof error === "object" &&
    error.type &&
    error.status !== undefined
  ) {
    return error as ApiErrorDetail;
  }

  const status = error?.response?.status || 0;
  const data = error?.response?.data;
  const isHtmlResponse = typeof data === "string" && containsHtml(data);
  const safeData = isHtmlResponse ? null : data;
  const nestedMessage = getFirstNestedMessage(safeData);

  const rawDetail = safeData?.detail;
  const rawMsgField = safeData?.message;
  const safeDetail =
    typeof rawDetail === "string" && !containsHtml(rawDetail) ? rawDetail : undefined;
  const safeMsgField =
    typeof rawMsgField === "string" && !containsHtml(rawMsgField) ? rawMsgField : undefined;

  let rawMessage =
    safeMsgField ||
    safeDetail ||
    nestedMessage;

  if (!rawMessage) {
    const fallback = getRawErrorMessage(error);
    rawMessage = containsHtml(fallback) ? "" : fallback;
  }

  let type: ApiErrorType = ApiErrorType.UNKNOWN;

  if (error instanceof ZodError) {
    type = ApiErrorType.VALIDATION;
  } else if (error?.code === "ECONNABORTED") {
    type = ApiErrorType.TIMEOUT;
  } else if (!error?.response) {
    type = ApiErrorType.NETWORK_ERROR;
  } else {
    switch (status) {
      case 400:
        type = ApiErrorType.VALIDATION;
        break;
      case 401:
        type = ApiErrorType.AUTHENTICATION;
        break;
      case 403:
        type = ApiErrorType.AUTHORIZATION;
        break;
      case 404:
        type = ApiErrorType.NOT_FOUND;
        break;
      case 409:
        type = ApiErrorType.CONFLICT;
        break;
      case 429:
        type = ApiErrorType.RATE_LIMIT;
        break;
      case 500:
      case 502:
      case 503:
      case 504:
        type = ApiErrorType.SERVER_ERROR;
        break;
    }
  }

  if (type === ApiErrorType.SERVER_ERROR || status >= 500) {
    type = ApiErrorType.SERVER_ERROR;
    if (!rawMessage || containsHtml(rawMessage) || rawMessage.length > 250) {
      rawMessage = "Error en el servidor. Por favor, intenta más tarde o contacta a soporte.";
    }
  }

  const message =
    error instanceof ZodError
      ? "Se recibieron actividades con un formato inesperado del backend."
      : type === ApiErrorType.NETWORK_ERROR ||
    rawMessage === "Network Error" ||
    rawMessage === "Failed to fetch"
      ? getNetworkErrorMessage()
      : (rawMessage || "Error desconocido");

  return {
    type,
    status,
    message,
    detail: safeDetail,
    errors:
      safeData?.errors ||
      (typeof safeData === "object" && safeData !== null && !safeData?.detail && !safeData?.message
        ? safeData
        : undefined),
    timestamp: new Date().toISOString(),
  };
}

/**
 * Crea una instancia de ApiError tipada
 */
export function createApiError(error: any): ApiError {
  const classified = classifyError(error);
  const apiError: ApiError = new Error(classified.message) as ApiError;

  apiError.type = classified.type;
  apiError.status = classified.status;
  apiError.originalError = error;
  apiError.errors = classified.errors;
  apiError.name = "ApiError";

  return apiError;
}

/**
 * Obtiene el mensaje de error mas apropiado segun el tipo
 * Prioriza mensajes legibles y previene exponer HTML o volcados tecnicos
 */
export function getErrorMessage(errorDetail: ApiErrorDetail): string {
  if (
    errorDetail.detail &&
    !containsHtml(errorDetail.detail) &&
    errorDetail.detail.length <= 250
  ) {
    return errorDetail.detail;
  }
  if (
    errorDetail.message &&
    errorDetail.message !== "Error desconocido" &&
    !containsHtml(errorDetail.message) &&
    errorDetail.message.length <= 250
  ) {
    return errorDetail.message;
  }

  switch (errorDetail.type) {
    case ApiErrorType.VALIDATION:
      return "Por favor, revisa los datos ingresados";
    case ApiErrorType.AUTHENTICATION:
      return "Credenciales invalidas o sesion expirada";
    case ApiErrorType.AUTHORIZATION:
      return "No tienes permisos para realizar esta accion";
    case ApiErrorType.NOT_FOUND:
      return "El recurso solicitado no fue encontrado";
    case ApiErrorType.CONFLICT:
      return "Existe un conflicto con los datos. Recarga e intenta nuevamente";
    case ApiErrorType.RATE_LIMIT:
      return "Has realizado demasiadas solicitudes. Intenta mas tarde";
    case ApiErrorType.SERVER_ERROR:
      return "Error en el servidor. Por favor, intenta más tarde o contacta a soporte.";
    case ApiErrorType.NETWORK_ERROR:
      return getNetworkErrorMessage();
    case ApiErrorType.TIMEOUT:
      return "La solicitud tardo demasiado tiempo. Intenta nuevamente";
    default:
      return "Ocurrio un error inesperado";
  }
}

/**
 * Extrae errores de validacion formateados para mostrar en formularios
 */
export function extractValidationErrors(
  apiError: ApiErrorDetail,
): Record<string, string> {
  if (!apiError.errors) {
    return {};
  }

  const formatted: Record<string, string> = {};

  if (typeof apiError.errors === "object") {
    Object.entries(apiError.errors).forEach(([field, messages]) => {
      if (Array.isArray(messages)) {
        formatted[field] = messages[0] || "Error de validacion";
      } else if (typeof messages === "string") {
        formatted[field] = messages;
      }
    });
  }

  return formatted;
}
