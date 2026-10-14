# 📋 API REST — Módulo SMU

> **Documento local:** está en `.gitignore` y **no se commitea**.
> La fuente autoritativa de la API sigue siendo OpenAPI: `GET /api/docs/`
> (tag **smu**) o `GET /api/schema/`.

| | |
|---|---|
| **Base URL** | `http://<host>:8000` |
| **Prefijo** | `/smu/` → `config/urls.py:39` incluye `apps.smu.urls` |
| **Router** | `DefaultRouter` en `apps/smu/urls.py:6` |
| **Alcance** | **Solo tomar y guardar**: 2 rutas, **ambas `POST`** (crear actividad y subir foto) |
| **Auth** | `Authorization: Bearer <JWT>` **o** header `X-API-Key: cinco_xxxxx` |
| **Permisos** | `IsAuthenticatedOrAPIKey` |
| **Throttle** | `APIKeyRateThrottle` → `429` si se excede |

---

## Endpoints

| Método | Ruta | Acción | Éxito |
|---|---|---|---|
| `POST` | `/smu/actividades/` | Crear actividad + subtablas (transaccional) | 201 |
| `POST` | `/smu/evidencias/` | Subir foto (multipart) → devuelve `ruta_archivo` | 201 |

**Flujo de las fotos (A1):** al guardar el formulario →
`POST /smu/evidencias/` por cada foto → se guarda `ruta_archivo` →
esas rutas viajan dentro de `evidencias[]` del
`POST /smu/actividades/`. La foto se sube **antes** de crear la actividad,
así que cae en `media/smu/evidencias/borrador/{seccion}/`.

### Lo que **no** existe (y no debe volver sin pruebas)

`GET /smu/actividades/` → **405** · `GET/PUT/PATCH/DELETE /smu/actividades/{id}/`
→ **404** (la ruta detalle ni se registra) ·
`PATCH /smu/actividades/{id}/cambiar-estado/` → **404** ·
`GET /smu/evidencias/` → **405**.

Decisión de alcance: *SMU solo toma datos y guarda*. La vista
`SmuActividadViewSet` expone únicamente `create`; el `DefaultRouter` descarta
el resto de acciones (`rest_framework/routers.py` → `if not mapping: continue`).
Esto cierra los hallazgos **M3** (endpoints sin consumidor), **M2**
(`delete+recreate` de `actualizar_actividad_smu`, ya eliminado junto con su
test), **B2** (`cambiar-estado`) y **A3** (sin paginación: no queda ningún
`GET` que paginar).

---

## `POST /smu/actividades/`

**Campos obligatorios** (los demás son opcionales): `categoria`,
`tipo_formulario`, `nombre_estacion`, `responsable_cedula`.

```bash
curl -X POST http://localhost:8000/smu/actividades/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "categoria": "preventivos",
    "tipo_formulario": "aire_acondicionado",
    "nombre_estacion": "ESTACIÓN NORTE",
    "responsable_cedula": "1020304050",
    "fecha_inicio": "2026-09-30T08:00:00-05:00"
  }'
```

- Crea cabecera + subtablas (técnicos, materiales, evidencias, transportes,
  detalle AA/Planta/Falla/CAPEX) en **una sola transacción**
  (`apps/smu/services/smu_actividad_service.crear_actividad_smu`).

### Validación de negocio → `400`

| Regla | Ejemplo de respuesta |
|---|---|
| `tipo_formulario` es una enumeración de 6 valores | `{"tipo_formulario": ["tipo_formulario no es válido. Opciones válidas: aire_acondicionado, planta, estandar, tipologia1, tipologia3, tipologia5."]}` |
| `categoria` ↔ `tipo_formulario` deben ser un par real | `{"tipo_formulario": ["El tipo de formulario 'estandar' no corresponde a la categoría 'preventivos'. Opciones válidas: aire_acondicionado, planta."]}` |
| Un solo bloque de detalle, y correspondiente al tipo | `{"non_field_errors": ["Solo puede enviarse un bloque de detalle por actividad; se recibieron: detalle_preventivo_aa, detalle_capex."]}` |
| `checklist_aa[].item_numero` entre 1 y 39 | `{"checklist_aa": [{"item_numero": ["item_numero debe estar entre 1 y 39."]}]}` |
| `fecha_fin` ≥ `fecha_inicio` | `{"fecha_fin": ["La fecha de fin no puede ser anterior a la fecha de inicio."]}` |
| `estado` inicial `aprobado` | se normaliza a `enviado` (no se puede auto-aprobar) |
| Choque de unicidad de BD | `{"detail": "Error de integridad en los datos: …"}` (400, no 500) |

**Pares válidos de `categoria` ↔ `tipo_formulario`:**

| `categoria` | `tipo_formulario` permitido |
|---|---|
| `preventivos` | `aire_acondicionado`, `planta` |
| `correctivos` | `estandar` |
| `emergencias` | `estandar` |
| `correctivos_capex` | `tipologia1`, `tipologia3`, `tipologia5` |

> El frontend construye el payload en `frontend/src/services/smu.service.ts`
> (`buildPreventivoAAPayload`, `buildPreventivoPlantaPayload`,
> `buildCorrectivoEmergenciaPayload`, `buildCapexTipologia{1,3,5}Payload`).
>
> **Flujo de fotos (Fase 3, 30/09):** cada builder acepta una cola opcional de
> pendientes y los 6 submits llaman a `subirPendientes()` → **`POST
> /smu/evidencias/` antes** del `POST /smu/actividades/`; la respuesta se pega
> en `evidencias[].ruta_archivo` (el `blob:` nunca viaja por la red). Si una
> subida falla se lanza `ErrorSubidaFotos` y **no se crea la actividad**.
> Ver `frontend/src/services/smu.service.ts` y `modules/smu/errors.ts`.

---

## `POST /smu/evidencias/` (multipart)

```bash
curl -X POST http://localhost:8000/smu/evidencias/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "archivo=@foto.jpg;type=image/jpeg" \
  -F "seccion=anexos_planta" \
  -F "campo_origen=slot_1"
```

**Entrada**: `archivo` (obligatorio), `seccion`, `campo_origen` (default
`campo`), `actividad_id` (opcional), `orden`, `descripcion`.

**Salida 201**:

```json
{
  "ruta_archivo": "smu/evidencias/borrador/anexos_planta/9f3c….webp",
  "url": "/media/smu/evidencias/borrador/anexos_planta/9f3c….webp",
  "nombre": "9f3c….webp",
  "bytes": 48210
}
```

**Validaciones → 400** (`{"archivo": ["…"]}`):

| Regla | Origen |
|---|---|
| Magic bytes: debe ser JPG / PNG / WebP real (niega SVG, GIF, HTML renombrado) | Pillow `Image.open().verify()` |
| `content_type` declarado ∈ `image/jpeg`, `image/png`, `image/webp` | 1ª barrera |
| Tamaño > 0 y ≤ **5 MB** | PHP `$maxArchivos`/`5 * 1024 * 1024` |
| `actividad_id` inexistente | FK |
| Tope de 5 fotos por campo (si `actividad_id` ya existe) | PHP `linea 555` |

**Lo que hace en disco**: re-encripta **siempre a WebP calidad 80** (equivalente
del `saveFiles()` del PHP), corrige la rotación EXIF y guarda con nombre
`uuid4()` en `media/smu/evidencias/{actividad_id | 'borrador'}/{seccion}/`.
Si Pillow no tuviera soporte WebP, conserva el formato original.

**Reglas en `POST /smu/actividades/` (relacionadas):**

- `evidencias[].ruta_archivo` rechaza `blob:` / `data:` → 400 con la
  instrucción de subir primero (esas URLs mueren al recargar).
- Máximo **5 evidencias por `campo_origen`** en el payload → 400
  (`Máximo 5 fotos por campo; …`). Campos distintos no se acumulan.

---

## Códigos de respuesta

| Código | Cuándo |
|---|---|
| 201 | Actividad creada |
| 400 | Validación de negocio o `IntegrityError` |
| 401 | Sin credenciales válidas |
| 403 | Sin permiso |
| 404 | Ruta detalle / `cambiar-estado` (no existen) |
| 405 | Método distinto de `POST` en la colección |
| 429 | Throttle superado |

---

## Notas

- **Tests:** `manage.py test apps.smu --settings=config.settings_test`
  (**29 tests**, corren sobre SQLite — no requieren MySQL). Incluye
  `SmuApiSoloPostTests` (la API es solo `POST`) y `SmuEvidenciaUploadTests`
  (11 tests de subida: WebP en disco, carpetas, magic bytes, 5 MB, tope 5,
  `blob:` rechazado).
- **Deuda que sigue abierta** (ver `diagnostico_smu_2026-09-28.md`): **A2** —
  permisos por objeto y registro de quién creó la actividad (`SmuActividad` no
  tiene `created_by`) —, la CI sin tests y la deuda técnica E1/E2.
  **Cerrados el 30/09:** A1 (fotos: backend + frontend conectado) y A4
  (timeout: 30 s normales, 120 s para subir).
- **Pendiente de deploy** (configuración, no de código): servir `/media/` fuera
  de DEBUG con `alias` en nginx, `MEDIA_ROOT` en volumen persistente y
  `client_max_body_size ≥ 6m` (por defecto nginx trae `1m` → 413 en fotos de 5 MB).
