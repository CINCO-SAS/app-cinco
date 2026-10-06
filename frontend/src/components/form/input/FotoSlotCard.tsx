import React, { useEffect, useRef, useState } from "react";
import { Check, Image as ImageIcon, Loader2, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import {
  FOTO_MAX_SIZE_MB,
  FOTO_ACCEPT,
  validarFotoCompleta,
  liberarPreviewUrl,
} from "@/lib/fotos";
import { fotoElegida, olvidarFotoElegida } from "@/lib/precargaFoto";

export { FOTO_MAX_SIZE_MB, FOTO_ACCEPT };
export { validarReglasBasicasFoto as validarFoto } from "@/lib/fotos";

interface FotoSlotCardProps {
  /** Número de orden visible en el badge (1-based) */
  index: number;
  /** Nombre/título del slot fotográfico */
  titulo: string;
  /** Descripción adicional opcional */
  descripcion?: string;
  /** URL de preview si ya hay una foto cargada */
  previewUrl?: string;
  /** ID único del input, usado para el htmlFor del label */
  inputId: string;
  /**
   * Callback al seleccionar un archivo ya validado.
   * Recibe el `File` directamente (no el evento) para evitar accesos a
   * eventos sintéticos stale después del `await` de validación.
   * Recibe `null` al eliminar la foto.
   */
  onUpload: (file: File | null) => void;
  /** Callback al presionar el botón de eliminar */
  onRemove: () => void;
  /** Tamaño máximo por foto en MB. Por defecto FOTO_MAX_SIZE_MB. */
  maxSizeMb?: number;
}

/**
 * Slot fotográfico estándar del sistema — componente global, reutilizable por
 * cualquier módulo:
 * `import FotoSlotCard from "@/components/form/input/FotoSlotCard"`
 *
 * `onUpload` recibe el `File` ya validado (no el evento) para garantizar que el
 * binario esté disponible incluso tras la espera asíncrona de validación.
 */
const FotoSlotCard: React.FC<FotoSlotCardProps> = ({
  index,
  titulo,
  descripcion,
  previewUrl,
  inputId,
  onUpload,
  onRemove,
  maxSizeMb = FOTO_MAX_SIZE_MB,
}) => {
  /** Último `File` entregado a `onUpload` (para olvidar su precarga al
   *  quitarlo o reemplazarlo). */
  const archivoRef = useRef<File | null>(null);
  /** Estado de la precarga en curso: solo se muestra si hay precargador. */
  const [precarga, setPrecarga] = useState<"subiendo" | "lista" | null>(null);
  /** Cierra el aviso "Subida" a los pocos segundos: en formularios con muchas
   *  fotos, badges permanentes solo ensucian (la info útil es "ya subió"). */
  const avisoRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cerrarAviso = () => {
    if (avisoRef.current) {
      clearTimeout(avisoRef.current);
      avisoRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      if (avisoRef.current) clearTimeout(avisoRef.current);
    };
  }, []);

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Limpiar el input ANTES del await para que el usuario pueda
    // re-seleccionar el mismo archivo si hay error.
    e.target.value = "";

    const error = await validarFotoCompleta(file, maxSizeMb);
    if (error) {
      toast.error(error);
      return;
    }

    // La foto anterior ya no sirve: si estaba precargada, se olvida.
    const anterior = archivoRef.current;
    if (anterior && anterior !== file) olvidarFotoElegida(anterior);
    archivoRef.current = file;

    // Precarga: si el módulo registró un subidor, la foto se sube YA, en
    // segundo plano; el guardado solo esperará la ruta (casi siempre lista).
    // Un fallo aquí no bloquea nada: se silencia y el guardado reintenta.
    cerrarAviso();
    const enCurso = fotoElegida(file);
    if (enCurso) {
      setPrecarga("subiendo");
      enCurso
        .then(() => {
          if (archivoRef.current !== file) return;
          setPrecarga("lista");
          avisoRef.current = setTimeout(() => {
            if (archivoRef.current === file) setPrecarga(null);
          }, 3000);
        })
        .catch(() => {
          if (archivoRef.current === file) setPrecarga(null);
        });
    } else {
      setPrecarga(null);
    }

    // Entregamos el File directamente: el evento ya puede haber sido
    // reciclado por React después del await.
    onUpload(file);
  };

  const handleRemove = () => {
    cerrarAviso();
    if (archivoRef.current) olvidarFotoElegida(archivoRef.current);
    archivoRef.current = null;
    setPrecarga(null);
    liberarPreviewUrl(previewUrl);
    onUpload(null);
    onRemove();
  };

  return (
    <div
      className={`group relative flex flex-col justify-between overflow-hidden rounded-xl border p-4 transition-all ${
        previewUrl
          ? "border-brand-500/40 bg-brand-50/20 dark:border-brand-500/30 dark:bg-brand-500/5"
          : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-800 dark:bg-white/2 dark:hover:border-gray-700"
      }`}
    >
      {/* Encabezado */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-[10px] font-bold text-gray-600 dark:bg-gray-800 dark:text-white/90">
              {index}
            </span>
            <p className="text-xs font-semibold text-gray-800 dark:text-white/90">
              {titulo}
            </p>
          </div>
          {descripcion && (
            <p className="text-[10px] text-gray-500 pl-7 dark:text-gray-400">
              {descripcion}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {/* Estado de la precarga (solo aparece si el módulo sube al elegir) */}
          {precarga === "subiendo" && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-600 dark:bg-brand-500/10 dark:text-brand-400"
              title="Subiendo la foto al servidor…"
            >
              <Loader2 className="h-3 w-3 animate-spin" />
              Subiendo…
            </span>
          )}
          {precarga === "lista" && (
            <span
      className="inline-flex items-center gap-1 rounded-full bg-success-50 px-2 py-0.5 text-[10px] font-medium text-success-600 dark:bg-success-500/10 dark:text-success-400"
              title="Foto ya en el servidor: el guardado no tendrá que subirla."
            >
              <Check className="h-3 w-3" />
              Subida
            </span>
          )}

          {previewUrl && (
            <button
              type="button"
              onClick={handleRemove}
              className="text-error-500 hover:bg-error-50 dark:hover:bg-error-500/10 rounded-md p-1 opacity-80 hover:opacity-100"
              title="Eliminar foto"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Área de preview o carga */}
      {previewUrl ? (
        <div className="relative aspect-4/3 w-full overflow-hidden rounded-lg border border-gray-200 bg-gray-900/5 dark:border-gray-700">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt={titulo}
            className="h-full w-full object-cover"
          />
          <label
            htmlFor={inputId}
            className="absolute right-2 bottom-2 flex cursor-pointer items-center gap-1 rounded-md bg-black/70 px-2 py-1 text-[11px] font-medium text-white backdrop-blur-xs transition-all hover:bg-black"
          >
            <Upload className="h-3 w-3" />
            Cambiar
          </label>
        </div>
      ) : (
        <label
          htmlFor={inputId}
          className="hover:border-brand-400 hover:bg-brand-50/30 dark:hover:border-brand-500 dark:hover:bg-brand-500/5 flex aspect-4/3 w-full cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 bg-gray-50/50 p-4 text-center transition-all dark:border-gray-700 dark:bg-white/1"
        >
          <div className="bg-brand-50 text-brand-500 dark:bg-brand-500/10 dark:text-brand-400 flex h-10 w-10 items-center justify-center rounded-full">
            <ImageIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Subir o Tomar Foto
            </p>
            <p className="text-[10px] text-gray-400">
              JPG, PNG, WebP · máx. {maxSizeMb} MB
            </p>
          </div>
        </label>
      )}

      <input
        id={inputId}
        type="file"
        accept={FOTO_ACCEPT}
        className="hidden"
        onChange={handleChange}
      />
    </div>
  );
};

export default FotoSlotCard;

