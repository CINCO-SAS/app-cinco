# Informe de análisis — Módulo de Configuraciones

**Fecha:** 2026-10-07
**Alcance:** análisis de solo lectura. **No se modificó, movió ni eliminó ningún archivo** (único artefacto nuevo: este informe).

---

## 1. Qué se analizó

**Frontend (`frontend/src/modules/configuraciones/`)**

| Archivo | Rol |
|---|---|
| `components/ConfiguracionesView.tsx` | Contenedor / layout del módulo (42 líneas) |
| `components/PerfilUsuarioCard.tsx` | Tarjeta de datos del usuario (92 líneas) |
| `components/CambioPasswordCard.tsx` | Formulario de cambio de contraseña (274 líneas) |
| `services/configuracion.service.ts` | Validación + llamada a la API (49 líneas) |
| `types/configuracion.types.ts` | Tipos del módulo (18 líneas) |
| `frontend/src/app/(private)/configuraciones/page.tsx` | Página Next.js |

**Backend (flujo asociado)**

- `apps/authentication/views/change_password_view.py`
- `apps/authentication/serializers/password_serializer.py`
- `apps/authentication/services/authentication_service.py` (`change_password`, líneas 183-208)
- `config/settings.py` (`AUTH_PASSWORD_VALIDATORS` 261-274, `REST_FRAMEWORK` 166-178)

**Contexto de estado:** `git status` muestra que el módulo es trabajo **nuevo y sin commitear** (`?? frontend/src/modules/configuraciones/`, `?? .../change_password_view.py`, más archivos modificados en `authentication`). Por eso el informe está orientado a corregir antes de mergear, no a deuda histórica.

---

## 2. Resumen ejecutivo

El módulo está **bien construido a nivel visual**: layout limpio, dark mode, checklist en tiempo real, loading state, mensajes de éxito/error, fallback de avatar. El código es legible y sigue la estructura de módulos del proyecto.

Los problemas están sobre todo en **seguridad y en la capa de validación**, no en la UI:

1. **P0 — La política de contraseñas del backend no se aplica nunca.** `AUTH_PASSWORD_VALIDATORS` está definido pero nadie lo ejecuta: `AuthenticationService.change_password` solo hace `set_password`. Se puede guardar `123456` o `aaaaaaaa`.
2. **P0 — Sin rate limiting en el endpoint.** El throttle global es `APIKeyRateThrottle` (solo aplica a peticiones con API Key), así que `/auth/change-password/` permite intentar la contraseña actual sin límite → fuerza bruta.
3. **P1 — Las sesiones abiertas no se revocan** al cambiar la contraseña: los refresh tokens de otros dispositivos siguen vivos.
4. **P1 — Validaciones muertas en el frontend**: `hasLetter` y `hasNumber` se calculan pero no se exigen ni se muestran.
5. **P2 — Manejo de errores no sigue el estándar del proyecto** (`getToastErrorMessage` / `classifyError`), con una cadena de `error.response.data` que es código muerto.

---

## 3. Hallazgos

### P0 — Seguridad

**H1. La validación de contraseña del backend nunca se ejecuta**
- `authentication_service.py:196-200` solo valida que la nueva sea distinta de la actual y luego `set_password(new_password)`.
- `password_serializer.py:6` solo impone `min_length=6`.
- `settings.py:261-274` define `UserAttributeSimilarityValidator`, `MinimumLengthValidator` (8), `CommonPasswordValidator` (listas de contraseñas comunes) y `NumericPasswordValidator`, pero **`validate_password` no aparece en ningún punto del código**.
- *Impacto:* contraseñas numéricas, comunes o iguales al usuario/username pasan sin más. La validación del frontend es prescindible (se puede llamar la API directamente).
- *Cambio sugerido:* llamar `django.contrib.auth.password_validation.validate_password(new_password, user=user)` dentro de `change_password` y devolver el mensaje vía `ValueError` (el `except ValueError` de la vista ya existe).

**H2. Sin límite de intentos en el cambio de contraseña**
- `change_password_view.py:15` usa `permission_classes = [IsUserOnly]` y ningún `throttle_classes`.
- `settings.py:174-176` solo registra `APIKeyRateThrottle`, que depende de `X-API-Key`.
- `authentication_service.py:190-194` ya registra en log el intento fallido, pero **no bloquea nada**.
- *Impacto:* un atacante autenticado puede probar la contraseña actual sin costo.
- *Cambio sugerido:* `ScopedRateThrottle` con `throttle_scope = "change-password"` (p. ej. 5/min) o un throttle por usuario.

### P1 — Seguridad y consistencia

**H3. No se revocan sesiones tras el cambio de contraseña**
- `change_password` (líneas 199-208) no toca `RefreshToken`; `logout` sí lo hace (`authentication_service.py:165-176`).
- `jwt_authentication.py` no ata el token a un hash/version de contraseña.
- *Impacto:* si la contraseña se cambia por robo o sospecha, el atacante sigue con sesión activa hasta expirar el refresh token. Tampoco hay opción "cerrar sesión en todos los dispositivos".
- *Cambio sugerido:* revocar todos los `RefreshToken` activos del usuario (excepto, opcionalmente, el actual) dentro de `change_password`.

**H4. Reglas de validación muertas en el frontend**
- `configuracion.types.ts:8-9` declara `hasLetter` / `hasNumber`; `configuracion.service.ts:8-9` las calcula.
- `CambioPasswordCard.tsx:41-45` (`isFormValid`) **no las usa**, y el checklist (líneas 208-242) solo muestra 3 de las 5 reglas.
- *Impacto:* el usuario ve un formulario que promete "validaciones de seguridad" incompletas, y la regla letra+número no existe en ningún lado (ni frontend ni backend).
- *Cambio sugerido:* decidir la política y aplicarla en **un solo lugar** (backend) reflejándola en el checklist.

**H5. Política de longitud contradictoria**
- Frontend y serializer: **6** caracteres (`configuracion.service.ts:7`, `password_serializer.py:6`).
- Django `MinimumLengthValidator`: **8** por defecto (`settings.py:266`).
- *Impacto:* en cuanto se active `validate_password`, empiezan a fallar contraseñas de 6-7 caracteres que el formulario mostraba como válidas.
- *Cambio sugerido:* alinear frontend, serializer y `MinimumLengthValidator(min_length=…)` a un único número.

**H6. Manejo de errores fuera del estándar del proyecto**
- `configuracion.service.ts:34-45` recorre `error?.response?.data?.detail`, `non_field_errors`, etc.
- Pero `api.ts:241` rechaza con el objeto **ya clasificado** (`ApiErrorDetail`), que **no tiene `.response`**: toda esa cadena es código muerto y solo sobrevive `error?.message`.
- El resto del proyecto usa `classifyError` + `getToastErrorMessage` (`frontend/src/lib/errorHandler.ts:231`, usado en `modules/smu/errors.ts:22`).
- *Impacto:* comportamiento aparentemente correcto hoy, pero frágil y difícil de mantener; si cambia `classifyError` nadie lo notará aquí.
- *Cambio sugerido:* `catch (error) { throw classifyError(error) }` y mostrar con `getToastErrorMessage` en el componente.

### P2 — Accesibilidad y UX

**H7. Formulario poco accesible** (`CambioPasswordCard.tsx`)
- `<label>` sin `htmlFor` (líneas 120, 148, 176) e `<input>` sin `id` ni `name` (127, 155, 183): el label no está asociado al campo.
- Sin `autoComplete="current-password"` / `"new-password"`: los gestores de contraseñas (y el "actualizar contraseña guardada" del navegador) no funcionan.
- Botones de mostrar/ocultar con `tabIndex={-1}` (139, 167, 195) y sin `aria-label`: **no se pueden operar con teclado** ni se anuncian a lectores de pantalla.
- Alertas de éxito/error sin `role="alert"` / `aria-live` (97-115): el cambio no se anuncia.
- *Sugerido:* `id`+`htmlFor`, `name`, `autoComplete`, `aria-label="Mostrar contraseña"`, quitar `tabIndex={-1}`, `role="alert"`.

**H8. Estados de avatar imposibles**
- `avatar.ts:15-18` **siempre** devuelve una URL (fallback `/images/user/owner.png`), así que en `PerfilUsuarioCard.tsx:26` y `:37` las ramas "sin avatar" (`avatarUrl ? …` y `hidden={!!avatarUrl}`) nunca se cumplen.
- El fallback a iniciales solo ocurre vía `onError` con mutación directa del DOM (líneas 31-34), que React puede reconciliar después.
- *Impacto:* bajo (funciona), pero el código comunica una lógica que no existe.

**H9. Dato potencialmente engañosso**
- `PerfilUsuarioCard.tsx:85`: `user?.area || "Operaciones / General"` muestra una sede por defecto aunque el usuario **no** tenga área cargada → el dato parece real y no lo es.
- `PerfilUsuarioCard.tsx:64-66`: etiqueta "Documento / Cédula" mapeada a `username`; correcto solo si el proyecto garantiza esa nomenclatura (ver `backend/REGLA_NOMENCLATURA_EMPRESA.md`). Conviene confirmarlo o mostrarlo como "Usuario".

### P3 — Calidad de código / mantenibilidad

- **`any` en los catches:** `configuracion.service.ts:34` y `CambioPasswordCard.tsx:70`. Con `error: unknown` + narrowing se aprovecha mejor TypeScript.
- **Sin tests:** no hay tests de `change_password` en `backend/apps/authentication/tests.py` (solo login/refresh/logout/health) ni del módulo en `frontend/tests/`. Además `frontend/package.json` tiene `"test": "echo \"No tests configured yet\""`.
- **Respuesta del backend vs. esquema documentado:** el servicio devuelve `{"success", "message"}` (`authentication_service.py:205-208`) pero el `extend_schema` de `change_password_view.py:22` documenta `{"detail": ...}`.
- **Sin `max_length` en `new_password`** (`password_serializer.py:6`): se puede enviar una contraseña de megabytes.
- **Trim silencioso:** DRF recorta espacios por defecto, así que una contraseña con espacios iniciales/finales se guarda sin ellos, sin avisar.
- **Sin barrel `index.ts`** en el módulo (otros módulos sí lo tienen parcialmente); los imports son rutas largas.
- **Tipado laxo de la respuesta:** `api.post<{ success?; message?; detail? }>` y luego `?? true` — si el backend no manda `success`, se asume éxito.

### Funcionalidad (producto)

El módulo se llama "Configuraciones" pero solo ofrece **perfil de solo lectura + cambio de contraseña**. No hay: editar foto/email/datos básicos, cerrar sesión en otros dispositivos, lista de sesiones activas, preferencias (tema/idioma) ni configuración de notificaciones. Vale la pena definir si el alcance actual es intencional.

---

## 4. Lo que está bien (no tocar)

- Estructura por módulo (`components/ / services/ / types/`) coherente con el resto de `frontend/src/modules`.
- Checklist de validación en tiempo real con estados visuales y botón deshabilitado según reglas (`CambioPasswordCard.tsx:41-45, 249-256`).
- El backend ya tiene `IsUserOnly` (bloquea API Keys), logging de intentos fallidos y `except ValueError` con mensaje amigable (`change_password_view.py:45-49`).
- Coherencia visual con dark mode y paleta de marca en todo el módulo.
- Detección de HTML en mensajes de error para no renderizar páginas de error de proxy (`configuracion.service.ts:43`) — buena intención (aunque hoy sea código muerto, ver H6).

---

## 5. Plan recomendado (pendiente de aprobación — nada ejecutado)

| Prioridad | Acción | Archivos |
|---|---|---|
| **P0** | Ejecutar `validate_password()` en el cambio de contraseña | `authentication_service.py` |
| **P0** | Throttle por usuario/ámbito en el endpoint | `change_password_view.py`, `settings.py` |
| **P1** | Revocar refresh tokens al cambiar contraseña | `authentication_service.py` |
| **P1** | Unificar política de contraseñas (longitud + letra/número) frontend↔backend | `password_serializer.py`, `configuracion.service.ts`, `CambioPasswordCard.tsx`, `settings.py` |
| **P1** | Adoptar `classifyError` + `getToastErrorMessage` | `configuracion.service.ts`, `CambioPasswordCard.tsx` |
| **P2** | Accesibilidad: `id/htmlFor`, `name`, `autoComplete`, `aria-*`, `role="alert"` | `CambioPasswordCard.tsx` |
| **P2** | Quitar el fallback de área inventado y revisar el mapeo "Documento/Cédula" | `PerfilUsuarioCard.tsx` |
| **P2** | Limpiar `any`, tipos de respuesta y documentación del esquema | `configuracion.*`, `change_password_view.py` |
| **P3** | Tests: `change_password` (backend) + validación del formulario (frontend) | `tests.py`, `frontend/tests/` |
| **P3** | Definir alcance futuro del módulo (perfil editable, sesiones, preferencias) | producto |

---

*Informe generado por análisis estático. Verificar H9 (nomenclatura de `username`) con el equipo antes de actuar.*
