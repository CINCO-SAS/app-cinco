# 🔒 Mejoras de Seguridad Implementadas

## Resumen
Este documento detalla las mejoras de seguridad implementadas en el sistema de autenticación.

## Cambios Implementados

### 1. ✅ Corrección de CORS (CRÍTICO)
**Archivo:** `backend/config/settings.py`

**Antes:**
```python
CORS_ALLOW_ALL_ORIGINS = True  # ❌ PELIGROSO
```

**Después:**
```python
CORS_ALLOW_ALL_ORIGINS = False  # ✅ Seguro
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://frontend.cincosas.com",
    "https://www.frontend.cincosas.com",
]
```

**Impacto:** Previene ataques CSRF desde dominios no autorizados.

---

### 2. ✅ SECRET_KEY Obligatoria (CRÍTICO)
**Archivo:** `backend/config/settings.py`

**Antes:**
```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'clave-hardcodeada')  # ❌
```

**Después:**
```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY debe estar configurada")  # ✅
```

**Impacto:** Impide iniciar la aplicación sin una SECRET_KEY única y segura.

**Acción requerida:**
```bash
# Generar nueva SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Agregarla a .env
echo "DJANGO_SECRET_KEY=tu-clave-aqui" >> .env
```

---

### 3. ✅ sessionStorage en lugar de localStorage
**Archivo:** `frontend/src/utils/storage.ts`

**Antes:**
```typescript
localStorage.setItem("user", JSON.stringify(user));  // ❌ Persiste entre sesiones
```

**Después:**
```typescript
sessionStorage.setItem("user", JSON.stringify(user));  // ✅ Solo durante la sesión
```

**Impacto:** Los datos se eliminan automáticamente al cerrar el navegador.

---

### 4. ✅ Cookies con SameSite='Strict'
**Archivos:** 
- `backend/apps/authentication/views/login_view.py`
- `backend/apps/authentication/views/refresh_view.py`

**Antes:**
```python
samesite='Lax'  # ❌ Permite algunas peticiones cross-site
```

**Después:**
```python
samesite='Strict'  # ✅ Máxima protección CSRF
```

**Impacto:** Las cookies nunca se envían en peticiones cross-site.

---

### 5. ✅ Security Headers en Producción
**Archivo:** `backend/config/settings.py`

**Agregado:**
```python
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # Forzar HTTPS por 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True  # Redirigir HTTP a HTTPS
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'  # Prevenir clickjacking
```

**Impacto:** Protección contra múltiples vectores de ataque.

---

### 6. ✅ Logging de Eventos de Seguridad
**Archivos:** 
- `backend/apps/authentication/views/login_view.py`
- `backend/apps/authentication/views/refresh_view.py`
- `backend/apps/authentication/views/logout_view.py`
- `backend/config/settings.py` (configuración)

**Eventos registrados:**
- ✅ Login exitoso
- ⚠️ Login fallido
- ⚠️ Intento sin credenciales
- ✅ Refresh exitoso
- 🔴 Token reuse detectado (posible ataque)
- ✅ Logout exitoso
- ⚠️ Logout sin token

**Ubicación de logs:** `backend/logs/security.log`

**Configuración:**
- Rotación automática cada 10 MB
- Mantiene 5 archivos históricos
- Formato: timestamp, nivel, módulo, mensaje

---

## Arquitectura de Seguridad

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                       │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │ sessionStorage                                      │    │
│  │ - Solo datos de usuario (NO tokens)                │    │
│  │ - Se borra al cerrar navegador                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Cookies HttpOnly (gestionadas por navegador)       │    │
│  │ - access_token: 15 min, Strict, HttpOnly          │    │
│  │ - refresh_token: 7 días, Strict, HttpOnly         │    │
│  │ - NO accesibles desde JavaScript                   │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS Only
                            │ CORS Restrito
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Django)                          │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │ JWT Authentication                                  │    │
│  │ - Valida token desde cookie (prioridad) o header   │    │
│  │ - Verifica device fingerprint                      │    │
│  │ - Tokens firmados con SECRET_KEY                   │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Refresh Token DB                                    │    │
│  │ - Rotación automática                              │    │
│  │ - Detección de reuso (revoca todos)                │    │
│  │ - Expiración: 7 días                               │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Security Logging                                    │    │
│  │ - Todos los eventos de auth                        │    │
│  │ - IP, username, timestamp                          │    │
│  │ - Rotación automática de logs                      │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Checklist de Despliegue

Antes de desplegar a producción:

- [ ] Configurar `DJANGO_SECRET_KEY` en variables de entorno
- [ ] Establecer `DJANGO_DEBUG=False`
- [ ] Verificar dominios en `CORS_ALLOWED_ORIGINS`
- [ ] Verificar dominios en `CSRF_TRUSTED_ORIGINS`
- [ ] Configurar certificado SSL/HTTPS
- [ ] Revisar logs periódicamente en `backend/logs/security.log`
- [ ] Configurar monitoreo de intentos de login fallidos
- [ ] Establecer alertas para detección de token reuse

---

## Mejoras Adicionales Recomendadas

### A corto plazo:
1. **Rate Limiting** - Limitar intentos de login (ej: 5 por minuto)
2. **2FA** - Autenticación de dos factores
3. **Password Policies** - Forzar contraseñas robustas

### A mediano plazo:
1. **IP Whitelist** - Para Panel Admin
2. **Anomaly Detection** - ML para detectar comportamiento anómalo
3. **Security Audits** - Revisión periódica con herramientas automatizadas

---

## Monitoreo de Seguridad

### Revisar logs regularmente:
```bash
# Ver últimos eventos
tail -f backend/logs/security.log

# Buscar intentos fallidos
grep "Failed login" backend/logs/security.log

# Buscar detección de reuso de tokens (CRÍTICO)
grep "Token reuse detected" backend/logs/security.log
```

### Alertas recomendadas:
- 🚨 **Token reuse detected** - Posible robo de tokens
- ⚠️ **+10 failed logins del mismo IP** - Posible ataque de fuerza bruta
- ⚠️ **+5 refresh failures consecutivos** - Posible problema de configuración

---

## Referencias

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/5.0/topics/security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [CORS Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

---

**Última actualización:** 2 de marzo de 2026
