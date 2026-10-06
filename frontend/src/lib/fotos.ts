/**
 * Módulo centralizado de validación, compresión y ciclo de vida de fotos.
 * Reutilizable en todos los módulos de la aplicación.
 */

export const FOTO_MAX_SIZE_MB = 5;

export const FOTO_MIME_PERMITIDOS = [
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;

export type FotoMimeType = (typeof FOTO_MIME_PERMITIDOS)[number];

export const FOTO_ACCEPT = "image/*";

/**
 * Clave del `File` compañero de un campo de foto "genérico" de CAPEX
 * (`foto_panoramica_preview` → `foto_panoramica_file`), siguiendo el patrón
 * que ya usan las actividades (`foto_antes_preview` / `foto_antes_file`).
 * Se usa para conservar el binario y poder subirlo al guardar (Fase 3).
 */
export function campoArchivoDeFoto(campo: string): string {
  return `${campo.replace(/_preview$/, "")}_file`;
}

/**
 * Valida los primeros bytes del archivo (Magic Bytes) para asegurar que el archivo
 * sea realmente una imagen válida y no un archivo renombrado o corrupto.
 */
export async function validarMagicBytes(file: File): Promise<boolean> {
  try {
    const buffer = await file.slice(0, 12).arrayBuffer();
    const bytes = new Uint8Array(buffer);

    // JPEG: FF D8 FF
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
      return true;
    }

    // PNG: 89 50 4E 47 0D 0A 1A 0A
    if (
      bytes[0] === 0x89 &&
      bytes[1] === 0x50 &&
      bytes[2] === 0x4e &&
      bytes[3] === 0x47 &&
      bytes[4] === 0x0d &&
      bytes[5] === 0x0a &&
      bytes[6] === 0x1a &&
      bytes[7] === 0x0a
    ) {
      return true;
    }

    // WebP: RIFF .... WEBP (bytes 0-3: 'RIFF', bytes 8-11: 'WEBP')
    if (
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x57 &&
      bytes[9] === 0x45 &&
      bytes[10] === 0x42 &&
      bytes[11] === 0x50
    ) {
      return true;
    }

    return false;
  } catch {
    return false;
  }
}

/**
 * Valida tamaño y extensión MIME básica (síncrona).
 */
export function validarReglasBasicasFoto(
  file: File,
  maxSizeMb: number = FOTO_MAX_SIZE_MB,
): string | null {
  if (!file || file.size === 0) {
    return `El archivo "${file?.name || ""}" está vacío o corrupto (0 bytes).`;
  }

  const maxSizeBytes = maxSizeMb * 1024 * 1024;
  if (file.size > maxSizeBytes) {
    const peso = (file.size / (1024 * 1024)).toFixed(1);
    return `"${file.name}" pesa ${peso} MB. El límite máximo es ${maxSizeMb} MB.`;
  }

  const esMimeValido = FOTO_MIME_PERMITIDOS.includes(file.type as FotoMimeType);
  if (!esMimeValido) {
    return `"${file.name}" no es un formato válido. Formatos permitidos: JPG, PNG, WebP.`;
  }

  return null;
}

/**
 * Valida de forma completa (tamaño + MIME + magic bytes).
 */
export async function validarFotoCompleta(
  file: File,
  maxSizeMb: number = FOTO_MAX_SIZE_MB,
): Promise<string | null> {
  const errorBasico = validarReglasBasicasFoto(file, maxSizeMb);
  if (errorBasico) return errorBasico;

  const esImagenReal = await validarMagicBytes(file);
  if (!esImagenReal) {
    return `"${file.name}" parece estar corrupto o no es una imagen válida real.`;
  }

  return null;
}

/**
 * Comprime una imagen a formato WebP/JPEG mediante Canvas en el navegador
 * para optimizar el ancho de banda y velocidad de subida.
 */
export async function optimizarFoto(
  file: File,
  maxWidth: number = 1920,
  maxHeight: number = 1920,
  calidad: number = 0.82,
): Promise<File> {
  return new Promise((resolve) => {
    // Si no es imagen o el navegador no tiene soporte de Image, devolver el original
    if (typeof window === "undefined" || !window.createImageBitmap) {
      resolve(file);
      return;
    }

    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);

      let { width, height } = img;
      if (width > maxWidth || height > maxHeight) {
        if (width > height) {
          height = Math.round((height * maxWidth) / width);
          width = maxWidth;
        } else {
          width = Math.round((width * maxHeight) / height);
          height = maxHeight;
        }
      }

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");

      if (!ctx) {
        resolve(file);
        return;
      }

      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (!blob || blob.size >= file.size) {
            // Si por alguna razón la compresión no reduce tamaño, conservamos el original
            resolve(file);
            return;
          }

          const baseName = file.name.replace(/\.[^/.]+$/, "");
          const optimizedFile = new File([blob], `${baseName}.webp`, {
            type: "image/webp",
            lastModified: Date.now(),
          });
          resolve(optimizedFile);
        },
        "image/webp",
        calidad,
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(file);
    };

    img.src = objectUrl;
  });
}

/**
 * Libera de forma segura un ObjectURL para evitar memory leaks.
 */
export function liberarPreviewUrl(url?: string | null): void {
  if (url && url.startsWith("blob:")) {
    try {
      URL.revokeObjectURL(url);
    } catch {
      // Ignorar si ya fue revocado
    }
  }
}
