import { useState, useCallback, useEffect, useRef } from "react";
import { liberarPreviewUrl, optimizarFoto } from "@/lib/fotos";

export interface FotoItemState {
  file: File | null;
  previewUrl: string | null;
  nombre?: string;
}

/**
 * Hook para gestionar el ciclo de vida de fotos en formularios:
 * - Genera previews usando ObjectURL.
 * - Revoca automáticamente URLs anteriores al cambiar o eliminar fotos.
 * - Revoca todos los blobs al desmontar el componente para evitar memory leaks.
 * - Opcionalmente optimiza la imagen a WebP.
 */
export function useFotoSlot(initialUrl?: string | null) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(initialUrl || null);
  const currentPreviewRef = useRef<string | null>(initialUrl || null);

  useEffect(() => {
    currentPreviewRef.current = previewUrl;
  }, [previewUrl]);

  // Limpieza al desmontar
  useEffect(() => {
    return () => {
      liberarPreviewUrl(currentPreviewRef.current);
    };
  }, []);

  const setFoto = useCallback(async (nuevoFile: File | null, optimizar: boolean = false) => {
    // Si se pasa null, eliminamos la foto
    if (!nuevoFile) {
      liberarPreviewUrl(currentPreviewRef.current);
      currentPreviewRef.current = null;
      setFile(null);
      setPreviewUrl(null);
      return;
    }

    // Si se pide optimizar
    const archivoFinal = optimizar ? await optimizarFoto(nuevoFile) : nuevoFile;

    // Liberar la preview anterior si existía
    liberarPreviewUrl(currentPreviewRef.current);

    const nuevaUrl = URL.createObjectURL(archivoFinal);
    currentPreviewRef.current = nuevaUrl;

    setFile(archivoFinal);
    setPreviewUrl(nuevaUrl);
  }, []);

  const clearFoto = useCallback(() => {
    setFoto(null);
  }, [setFoto]);

  return {
    file,
    previewUrl,
    setFoto,
    clearFoto,
  };
}
