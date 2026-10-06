# Estudio: función de captura de fotos (legacy PHP) → componentes SMU

_Fecha: 2026-09-29_

**Fuentes**

- `C:\Users\admin\Documents\funcionalidades genericas\tratamiento de datos\smu_reporte_actividades.php` (13.379 líneas)
- `C:\Users\admin\Documents\funcionalidades genericas\tratamiento de datos\controller_cinco.php` (`saveFiles()`, línea 1586)

**Objetivo**: entender la idea de captura de fotos del PHP legado y trasladarla a los
componentes reutilizables de imágenes de SMU en `frontend/src/modules/smu/components/common/`.

---

## 1. Cómo funciona la captura de fotos en el PHP

### 1.1 Flujo completo

```
<input type="file" multiple>  (HTML)
        │  change → valida image/*, preview con FileReader, tope 5 fotos (DataTransfer)
        ▼
FormData(form) + fetch(POST)          ← enviarFormularioCapex() / enviarFormularioGenerico()
        │  formData.append('ajax', 'new_form_capex_tipologia1' | ...)
        ▼
capex_procesar_archivos($_FILES, [...campos], carpeta, prefijo, fecha, &errores)
        │  valida y genera nombre único
        ▼
saveFiles(archivo, nombre, carpeta, ext, 0)   ← controller_cinco.php:1586
        │  re-encripta SIEMPRE a WebP (calidad 80) y mueve a disco
        ▼
INSERT INTO documentacion_actividades_smu (imagenes, detalle, edit)
        └── imagenes = JSON  {campo: ["ruta/relativa/archivo.webp", ...]}
            detalle  = JSON  (datos del formulario)
            edit     = cédula del usuario en sesión
```

### 1.2 `capex_procesar_archivos()` — la pieza central (línea 497)

```php
capex_procesar_archivos(array $files, array $campos, string $carpeta_relativa,
                        string $prefijo_archivo, string $fecha_num,
                        array &$errores_archivos): array
```

**Tres formas de `$_FILES` que sabe interpretar:**

| Forma | Ejemplo de input | Cuándo |
|---|---|---|
| Simple (un archivo) | `name="panoramica_foto"` | SPT, panorámica, gráficos |
| Múltiple (1 nivel) | `name="t1_fotos_antes[]"` | fotos antes/después, transporte |
| Anidada por fila (2 niveles) | `name="t1_foto_inventario[0][]"` | foto por insumo del inventario |

La forma anidada se detecta mirando si el primer `name` es array y se procesa con
**recursión**: llama otra vez a `capex_procesar_archivos()` por fila con prefijo
`{prefijo}_fila_{i}` y arma `{campo: {fila: [rutas]}}`.

**Validaciones, en orden:**

1. Carpeta destino escribible → `ssta_prepare_upload_dir()` (línea 17): `mkdir 0777` + `is_writable`.
2. Máximo **5 fotos por campo** (`$maxArchivos = 5`, línea 555) → si se excede, error y se omite **todo el campo**.
3. Error de subida PHP (`UPLOAD_ERR_*`) → `UPLOAD_ERR_NO_FILE` se ignora, el resto es error.
4. Tamaño ≤ **5 MB** (`5 * 1024 * 1024`, línea 583).
5. **MIME real** con `finfo_file()` (no la extensión): `image/jpeg`, `image/jpg`, `image/png`, `image/webp`.
6. Nombre único (línea 608):
   `{prefijo}_{fecha YmdHis}_{campo_saneado}_{índice}_{uniqid()}` + extensión original.

**Retorno**: `[campo => [rutas_relativas...]]` o `[campo => [fila => [rutas]]]`.
Las rutas se guardan **relativas** a la raíz del proyecto:
`archivos/smu_reporte_actividades/correctivos_capex1/capex_t1_20260929_..._abc123.webp`.

**Errores**: se acumulan en `$errores_archivos` (pasado por referencia) y **solo se
escriben en `error_log`** — el usuario nunca los ve (ver §4).

### 1.3 `saveFiles()` — escritura en disco (`controller_cinco.php:1586`)

```php
saveFiles($files_input, $file_name_save, $dir_src, $ext = false, $max_size_mb = 1)
```

- Extensiones permitidas: `jpg, png, jpeg, gif, webp, pdf`.
- **Dato clave**: `capex_procesar_archivos()` lo invoca con `$max_size_mb = 0`
  (línea 610), entonces `$optimize = $size > 0` → **siempre** re-encripta la imagen a
  **WebP calidad 80** con GD (`imagewebp($lienzo, ..., 80)`).
- Si GD falla o no está disponible → `move_uploaded_file()` con la extensión original.
- Devuelve `['success', 'file_name_save' (ruta absoluta), 'file_name', 'extension']`.

### 1.4 Frontend PHP

- `initFileNames()` (línea 13164): valida `file.type.startsWith('image/')`, muestra
  "N archivos validos seleccionados" y preview con `FileReader.readAsDataURL`.
- Tope de fotos (línea 13314): `MAX_FOTOS = 5` con un `DataTransfer` acumulador —
  las fotos excedentes se descartan con `alert()` antes de enviar.
- `validarForm()` (línea 13250): los `[data-required]` de tipo `file` exigen al menos un archivo.
- Envío: `new FormData(form)` → `fetch(window.location.href, {method:'POST'})` → JSON
  `{ok, error, msg, id}` → `Swal.fire` → `location.reload()`.

### 1.5 Reglas que vale la pena portar

| Regla | Valor en PHP |
|---|---|
| Formatos aceptados | JPG / PNG / WebP (validados por MIME real, no por extensión) |
| Tamaño máximo | 5 MB por foto |
| Tope de fotos por campo | 5 |
| Nombre en disco | prefijo + fecha + campo + índice + id único (nunca el nombre original) |
| Organización | una carpeta por formulario (`correctivos_capex1/2/3`, `preventivo_aa`, ...) |
| Previsualización | sí, antes de enviar |
| Errores | acumulados y devueltos (aquí es donde hay que mejorarlos) |

### 1.6 Bugs del legacy que NO conviene copiar

1. **HTML promete más que PHP**: la ficha de planta anuncia "Máximo 15 fotos" por
   sistema, pero `$maxArchivos = 5` es global → las excedentes se descartan en silencio
   (solo `error_log` en `form_preventivo_planta`).
2. **El usuario nunca ve los errores de archivo**: `$errores_archivos` solo hace `error_log`.
3. **Tipología 1 doble-codifica** `$detalle` (`json_encode` en línea 685 y otra vez en 738).
4. `ssta_uploaded_evidence_file()` está definida y **no se usa** en ningún lado.
5. **La foto vive solo en disco + una ruta en JSON**: no hay relación filial con el
   registro ni historial; y en el nuevo sistema pasaría lo mismo si solo se guardara
   la preview (ver §2).

---

## 2. Estado actual en app-cinco (SMU)

| Pieza | Archivo | Estado |
|---|---|---|
| Slot de foto genérico | `frontend/src/components/form/input/FotoSlotCard.tsx` | ✅ nuevo hoy (§3) |
| Slot + descripción genérico | `frontend/src/components/form/input/FotoSlotWithDescripcion.tsx` | ✅ nuevo hoy (§3) |
| Llamada de los formularios | 16 archivos SMU → `@/components/form/input/...` | ✅ directa a components (§3) |
| Migraciones BD | `backend/apps/smu/migrations/0001 → 0003` | ✅ **aplicadas por el usuario** |
| Sliders (20+ usos) | `capex/tipologia*/Paso*.tsx`, `preventivos/*`, `correctivos/*` | ⚠️ guardan solo `URL.createObjectURL(file)` → el `File` se descarta |
| Builder de payload | `frontend/src/services/smu.service.ts` → `evidencia()` | ⚠️ escribe metadatos; `ruta_archivo` = identificador del campo, no una ruta |
| Modelo | `backend/apps/smu/models/smu_actividades.py:220` `SmuActividadEvidencia` | ✅ listo: `seccion`, `campo_origen`, `ruta_archivo`, `nombre_original`, `descripcion`, `orden` |
| Servicio | `backend/apps/smu/services/smu_actividad_service.py:76` | ✅ crea las filas de evidencia |
| MEDIA_ROOT / MEDIA_URL | `backend/config/settings.py` | ❌ no existe (Pendiente B) |
| Endpoint multipart | `POST /smu/evidencias/` | ❌ no existe (Pendiente B) — el único `MultiPartParser` del backend está en `apps/empleados` |

**Conclusión del diagnóstico**: el modelo y el servicio ya soportan evidencias; lo que
falta es el **binario**. Hoy la foto es un blob de preview efímero que muere al recargar.

---

## 3. Cambio realizado (Fase 1 — dos componentes, llamada directa)

**Forma final (la más simple)**: solo dos archivos, en la carpeta donde ya viven
los inputs de formulario, y los módulos los importan directo — sin capas intermedias,
sin adaptadores y sin archivo de utilidades aparte.

### Archivos nuevos

1. **`frontend/src/components/form/input/FotoSlotCard.tsx`** — el slot foto:
   - Constantes + validación aquí mismo (espejo del PHP):
     `FOTO_MAX_SIZE_MB = 5`, `FOTO_TIPOS_PERMITIDOS` (jpeg/jpg/png/webp),
     `FOTO_ACCEPT = 'image/*'` (el móvil sigue ofreciendo cámara) y
     `validarFoto(file, maxSizeMb)` → mensaje de error o `null`.
   - `onChange` propio: valida **antes** de notificar al formulario; si es
     inválida limpia el input (permite re-elegir el mismo archivo) y lanza
     `toast.error` (sonner, el mismo que usan los sliders). Si es válida →
     `onFileChange?.(file)` y luego `onUpload(e)` **sin romper la firma existente**.
   - **Prop opcional `onFileChange?: (file: File | null) => void`**: entrega el
     binario validado (y `null` al eliminar) — es el punto de enganche con el
     endpoint de subida (Tarea B). La preview por sí sola es un blob efímero.
   - **Prop opcional `maxSizeMb`** (default 5).
   - UI honesta: `JPG, PNG, WebP · máx. 5 MB` (antes decía "hasta 10MB" sin validar).
2. **`frontend/src/components/form/input/FotoSlotWithDescripcion.tsx`** —
   compone el slot + textarea de descripción y delega `onFileChange`/`maxSizeMb`.

### Llamada desde cualquier módulo (nuevo o existente)

```tsx
import FotoSlotCard from "@/components/form/input/FotoSlotCard";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
```

### Limpieza en SMU

- **16 archivos actualizados** a la llamada directa: los `Paso2…Paso7` de CAPEX
  tipología 1/3/5 + `FormPreventivoAASlider` + `FormCorrectivoEmergenciaSlider`.
- **Eliminados** `modules/smu/components/common/FotoSlotCard.tsx` y
  `FotoSlotWithDescripcion.tsx` (ya no hay doble capa).
- `modules/smu/components/common/index.ts` ya no los exporta.

**Verificación**: `npx.cmd prettier --write` + `npx.cmd eslint` → OK.
`npx.cmd tsc --noEmit` → solo el error preexistente de
`AppSidebar.tsx` (TS7016, documentado como preexistente); los 16 imports nuevos
compilan sin errores.

---

## 4. Fases siguientes (propuesta)

### Fase 2 — Backend + servicio de subida (Pendiente B)

> Las migraciones `0001` → `0003` de `smu` **ya están aplicadas**; esta fase no
> requiere ninguna migración nueva (no cambian modelos).

1. `config/settings.py`: `MEDIA_ROOT` + `MEDIA_URL` y servir `static/`/`media/` en `urls.py`.
2. `POST /smu/evidencias/` (multipart, `MultiPartParser`, patrón de `apps/empleados`):
   - entrada: `archivo`, `seccion`, `campo_origen`, (`actividad_id` opcional), `orden`, `descripcion`
   - valida MIME real (Django `content_type` + Pillow) y tamaño ≤ 5 MB
   - guarda con nombre generado (`uuid4`, nunca el nombre original) en
     `media/smu/evidencias/{actividad|borrador}/{seccion}/`
   - **equivalente Django de `saveFiles()`**: Pillow → re-encriptar a WebP q80
   - devuelve `ruta_archivo` para que el front la meta en el payload
3. `smu.service.ts`: `subirEvidenciaSMU(file, {seccion, campo_origen, ...})`.
   > No requiere migración: no cambian modelos.

### Fase 3 — Conectar los formularios

1. Los sliders guardan el `File` que hoy entrega `onFileChange` (junto al preview).
2. Al seleccionar o al submit (decisión pendiente, §5) → `subirEvidenciaSMU` →
   quedarse con `ruta_archivo`.
3. `evidencia()` en `smu.service.ts` usa la ruta real en `ruta_archivo` en lugar del
   identificador de campo / blob.
4. Reglas de negocio (tope de fotos por sección) alineadas entre HTML y backend — el
   bug 1 de §1.6.

### Correspondencia PHP → Django/React

| PHP legacy | Django / React |
|---|---|
| `finfo_file()` (MIME real) | `content_type` + Pillow `Image.open().verify()` |
| `5 * 1024 * 1024` | `DATA_UPLOAD_MAX_MEMORY_SIZE` + validación en la view |
| `$maxArchivos = 5` | constante compartida front/back por sección |
| `uniqid()` + `YmdHis` | `uuid4()` + `datetime` |
| `saveFiles()` → WebP q80 | Pillow `img.save(..., "WEBP", quality=80)` |
| `ssta_prepare_upload_dir()` | `os.makedirs(MEDIA_ROOT/..., exist_ok=True)` |
| carpeta `archivos/{formulario}/` | `media/smu/evidencias/{actividad}/{seccion}/` |
| JSON `imagenes` en una columna | filas de `SmuActividadEvidencia` (ya existe) |
| `$errores_archivos` → `error_log` | `400` con `detail` → `toast.error` |

---

## 5. Decisiones pendientes (preguntar antes de la Fase 2)

1. **¿Subir la foto al seleccionarla o al guardar el formulario?**
   - Al seleccionar: el binario ya está en el servidor aunque falle el submit, pero
     quedan fotos huérfanas si el usuario cancela.
   - Al guardar: una sola petición por formulario, pero si falla se pierden todas.
   - (Mi lectura del PHP: lo hace al guardar, en la misma petición. Alternativa híbrida:
     subir al seleccionar y solo confirmar en el submit.)
2. **¿5 MB o 10 MB?** El PHP dice 5; el texto viejo del componente decía 10.
   Hoy quedó en **5** (constante `FOTO_MAX_SIZE_MB`).
3. **¿Comprimir en el cliente (canvas → WebP) antes de subir?** El PHP comprime en el
   servidor con GD; en el front se puede bajar el payload del upload.
4. ** Carpeta por actividad o por usuario/fecha?** Afectaría cómo se borra después.
5. **¿Borrar las fotos del servidor si el usuario elimina el slot?** (limpieza de huérfanos)

---

## 6. Reglas de la sesión vigentes

- **Migraciones `0001` → `0003` de `smu` YA aplicadas** por el usuario (los modelos
  nuevos de la auditoría ya están en BD). Aun así, avisar antes de correr `migrate`.
- No hacer `commit` sin pedirlo (hay cambios propios sin commitear en `backend/`,
  `frontend/` y `frontend/src/modules/smu/` es *untracked*).
- La Fase 2 propuesta no requiere migración: solo `settings.py`, `urls.py`, una view
  y el servicio del front.
