# Backend del Módulo Transporte — De la propuesta 2026 a la implementación real
## Documento de exposición: qué tenemos, qué se propone, cómo se aplica y qué se mejora

**Fecha:** 13 de Octubre de 2026
**Propósito:** exponer, con lo que realmente se cuenta hoy, la idea de backend del [`PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md), explicar cómo se aplica y presentar las mejoras incorporadas. **No transcribe el plan:** cita solo lo necesario.
**Base documental:** [`PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md) · [`PLAN_MIGRACION.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_MIGRACION.md) (revisión 13-10) · [`PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md) · [`DICCIONARIO_DATOS.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/DICCIONARIO_DATOS.md) · [`ANALISIS_TRANSPORTE_BASE_CONDUCTORES.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/ANALISIS_TRANSPORTE_BASE_CONDUCTORES.md).

---

## 1. Con qué se cuenta realmente (lo verificado, no lo supuesto)

### 1.1 Código fuente disponible en la carpeta

| Archivo | Líneas | Qué se verificó | Estado |
|---|---|---|---|
| [`base_salida_transporte.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_salida_transporte.php) (+ `.fix`) | ~3.100 | **3 pestañas** reales: "Base Salida" (backoffice con 15 herramientas), "Info" (include de informes), "Datos" (include de parámetros). 15 acciones API. Validación masiva, rechazo con motivo, novedades, semáforo SOAT/CDA, fecha límite de cierre | Analizado íntegramente |
| [`transporte_salida.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_salida.php) | ~2.139 | Registro operativo: QR/cámara, asignar móvil, validación anticolisión (vehículo-día y móvil-día con `estado != 'ELIMINADO'`), ventana de -2 días hábiles, planilla. **Escribe en la base negra** (`nokia_base_infraestructura`) | Analizado íntegramente |
| [`base_transportadores.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_transportadores.php) | ~3.099 | ABM flota: ficha de 50+ campos, fotos, datos bancarios en JSON, import CSV, QR, cruces de teléfonos con Nokia | Analizado (API + UI) |
| [`transporte_base_conductores.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_base_conductores.php) | 578 | ABM conductores completo (análisis propio en documento dedicado): alta/edición, edad calculada en JS, alta sin `fecha_egreso`, punto de inyección SQL en el UPDATE | Analizado íntegramente |

### 1.2 Datos reales (estructura y volúmenes, de `DICCIONARIO_DATOS.md`)

- **3 tablas principales:** `transportadores_vehiculos` (~1.246 filas, 55 columnas, placa **sin** unique), `transporte_registro_salida` (~200.811 filas, 11 columnas + JSON `datos` + longtext `historial`), `transporte_base_conductores` (~108 filas, sin índice en cédula).
- **10 tablas de apoyo referenciadas en código:** personal, fechas límite, consecutivos, validación de salidas, log, jefes (`programacion_parametros`), áreas (`infraestructura_parametros`), `config_menu` y base negra Nokia.
- **Sin ninguna FK ni UNIQUE en toda la base del módulo.** Cédulas con 3 tipos distintos; JSON con bancarios, pagos, novedades e historial adentro; fechas `'0000-00-00'`; typos (`cedual_conductor`, `ultima_revicion`); cotejamientos mezclados.

### 1.3 Funcionalidades confirmadas (inventario "nada se pierde")

Toda herramienta de interfaz fue trazada con su regla y evidencia en código (§1.5–§1.6 de `PLAN_MIGRACION.md`): 15 herramientas del backoffice (B1–B15), 6 del kiosco (S1–S6), 6 de flota (T1–T6), conductores (C1), más las pestañas Informes (I1) y Datos (D1–D4) y las dependencias externas (E1–E3: controlador `gerencia_informes_vehiculos_controlador`, helpers JS globales, cédulas hardcodeadas en el frontend).

### 1.4 Lo que NO se tiene (y condiciona el arranque)

`transporte_salida_informes.php`, `transporte_salida_datos(_fix).php`, `planilla_salida.php`, `transporte_reporte_vehiculo_inc.php`, `controller_cinco.php`, `configure.php`, `header.php`, el controlador externo y el JS compartido. Además, **ninguna tabla del módulo está verificada contra duplicados aún** (auditoría pendiente).

---

## 2. Qué propone el plan 2026 (citando solo lo esencial)

El plan 2026 (v2.0) fija la arquitectura de destino. Sus propuestas centrales, textualmente resumidas:

1. **Estrategia:** *"Construcción en Paralelo + Corte Único"* — el PHP opera sin alteración, Django se construye en paralelo, corte con *"rollback inmediato (menos de 2 minutos vía puntero de menú)"*.
2. **Modelo de datos:** *"Adopción Estricta de ID Foreign Keys"* y *"Separación de Conductores Externos vs. Empleados de Nómina"* — los transportistas externos que no existen en la nómina se modelan como entidad autónoma `Conductor`.
3. **Backend:** Django con patrón **`ViewSet → Service → Serializer`**, *"Capa de Servicios Única (services.py): ninguna vista contendrá lógica de negocio"*. Define 5 modelos (Conductor, Vehiculo, Salida, ReporteFotograficoVehiculo, ConsecutivoMensual) y 3 servicios (SalidaService, LiquidacionService, ReporteFotograficoService).
4. **Alcance ampliado:** 7 módulos funcionales, incluyendo dos que **no existen en esta carpeta**: reporte fotográfico diario (validando agenda en `operaciones_agenda` y ventana 10a–4p) y planilla oficial con QR.
5. **Reglas clave a preservar:** semáforo SOAT/CDA (verde/naranja/rojo), anticolisión doble, ventana de -2 días hábiles, aprobación masiva por área del jefe, rechazo con motivo, consecutivos atómicos con `select_for_update()`.
6. **Ecosistema:** asume apps heredadas `common.Area` y `empleados.Empleado` (ADMCINCO) y destino MySQL `utf8mb4`.

---

## 3. La idea de backend aplicada — cómo se traduce en la realidad que tenemos

### 3.1 Estructura del proyecto (organización canónica `app-cinco`)

La organización del código se acopla directamente a la estructura real existente en el repositorio **`app-cinco`** (`c:\Users\admin\Documents\app-cinco`), respetando el patrón corporativo **`ViewSet -> Service -> Serializer`**:

```text
app-cinco/
├── backend/
│   ├── config/                     # settings, wsgi, asgi, enrutamiento global
│   ├── apps/
│   │   ├── authentication/         # Control de acceso y sesiones
│   │   ├── common/                 # Area, Festivos, AuditoriaModel, menu
│   │   ├── empleados/              # Empleado (personal corporativo referenciado; NO se migra)
│   │   ├── operaciones/            # OTs y agendas operativas (validación de fotos)
│   │   └── transporte/             # Módulo Transporte (nueva app modular):
│   │       ├── migrations/         # Esquema relacional MySQL 8
│   │       ├── models/             # ~16 modelos relacionales (§3.2)
│   │       ├── services/           # 9 servicios con TODA la regla de negocio (§3.3)
│   │       ├── serializers/        # Validación y contratos de entrada/salida
│   │       ├── views/              # ViewSets (ViewSet -> Service -> Serializer)
│   │       ├── admin.py
│   │       ├── apps.py
│   │       ├── urls.py             # Rutas y endpoints REST del módulo
│   │       └── tests.py            # Pruebas de reglas de negocio y regresión
│   ├── manage.py
│   └── requirements.txt
└── frontend/
    └── src/
        └── modules/
            ├── configuraciones/
            ├── operaciones/
            ├── rrhh/
            └── transporte/         # Vistas frontend unificadas (Kiosco, Backoffice, Flota, Pagos)
```

La separación **Conductor externo vs Empleado** que propone el plan 2026 encaja perfectamente con lo verificado: el cruce real `get_telefonos_conductores` busca la misma cédula tanto en `cinco_base_de_personal` como en `transporte_base_conductores` — es decir, el negocio ya distingue las dos fuentes, pero en PHP lo hace con dos consultas sueltas; el backend lo convierte en dos modelos con relación explícita.

### 3.2 Modelos: la propuesta de 5 modelos, completada a la realidad

El plan 2026 modela bien el corazón (`Salida`, `Vehiculo`, `Conductor`), pero la funcionalidad verificada exige el resto. Así queda el mapa **propuesto → aplicado**:

| El plan 2026 define | La realidad verificada exige además | Por qué (evidencia) |
|---|---|---|
| `Salida` | `SalidaHistorial` (filas, no JSON) y `Novedad` (1 por salida) | El `historial` longtext y `datos.novedad` son el sustento del flujo reportado→aprobado/rechazado/validado y del cálculo de pago |
| `Vehiculo` | `DocumentoVehiculo`, `Mantenimiento` (1:N), `DatosBancariosVehiculo` | 4 imágenes en texto plano, 6 columnas que guardan solo el último mantenimiento, y bancarios/pagos escondidos en el JSON `datos` |
| — | `FechaLimiteCierre`, `PagoVehiculoMensual`, `JefeValidador`, `ValidacionSalida`, `AuditoriaLog`, `Festivo` | Son las tablas de apoyo reales que hoy sostienen cierres, sábanas, jefes por área/carpeta, log y la ventana de -2 días |

Todos los modelos nacen sobre `AuditableModel` (`creado_por/en`, `modificado_por/en`), reemplazando los `edit`/`fecha_edit` que hoy existen "a medias" en las tres tablas.

### 3.3 Servicios: una sola implementación de cada regla

La regla "services.py es la única capa de negocio" se aplica mapeando **cada comportamiento verificado del PHP a un método con nombre y contrato explícitos**:

- `SalidaService.registrar_salida()` — ventana de 2 días hábiles con festivos, anticolisión (vehículo-día y móvil-día), exigencia de área/carpeta cuando sale "disponible", snapshot de `valor_dia`, historial y log en transacción. Hoy ese código vive **4 veces**: en el PHP de registro, en el PHP de gestión, en el JS de la tabla y en el JS del modal de novedad.
- `SalidaService.aprobar_masivo()` — la validación por jefe de área/carpeta que hoy es la función JS `isUserLeaderOfSalida` (leen `programacion_parametros` en JSON) pasa a consulta sobre `JefeValidador`.
- `SalidaService.rechazar(id, motivo)` — motivo obligatorio, como el formulario actual.
- `SalidaService.registrar_novedad()` / `eliminar_novedad()` — adicional/descuento con `total = valor_dia ± novedad`, calculado **en servidor** (hoy se calcula en el JS del Swal).
- `LiquidacionService.obtener_o_generar_consecutivo()` con `select_for_update()` — mata la carrera `MAX+1` que el PHP intenta contener con `beginTransaction` artesanal.
- `PermisoService` — traduce **cada cédula hardcodeada encontrada** (admin, `permi_especial` 1000756621, `permi_editar_fecha`, la cédula 1055837370 que elige la pestaña Datos `_fix`, el perfil carpeta TRANSPORTE) a grupo o permiso Django.

### 3.4 Endpoints: la funcionalidad manda, no los archivos

El backend no se diseña "un endpoint por archivo PHP" sino **una matriz funcionalidad → endpoint → servicio → modelo** con 33 filas (B1–B15, S1–S6, T1–T6, C1, I1, D1–D4, F1, E1–E3, de `PLAN_BACKEND_DJANGO_CONSOLIDADO` §6). Así, la consolidación de pantallas propuesta en ambos planes (Registrar tablet separado de Gestión escritorio, parámetros en una sola pantalla, pagos como sección del vehículo) no pierde ninguna herramienta: cada botón, modal o flujo del JS actual tiene su fila y su estado de verificación antes del corte.

---

## 4. Mejoras incorporadas sobre la propuesta 2026

Son las correcciones que el análisis del código real obliga a hacer (detalle técnico en `PLAN_BACKEND_DJANGO_CONSOLIDADO` §1):

### 4.1 Los constraints únicos deben respetar el estado (la mejora crítica)

El plan 2026 propone:
> `UniqueConstraint(fields=['vehiculo', 'fecha_salida'])` y `UniqueConstraint(fields=['conductor', 'fecha_salida'])`

Pero el código de alta real (`transporte_salida.php` 447–458) valida duplicados con **`estado != 'ELIMINADO'`**: si una salida fue eliminada, el negocio **permite registrar otra el mismo día**. Un unique incondicional **bloquearía un flujo legítimo** y haría fallar el ETL histórico (que contiene filas ELIMINADO conviviendo con salidas vivas del mismo día).

**Mejora aplicada:** constraints **parciales** con `condition=~Q(estado='ELIMINADO')`, tanto para vehículo como para conductor. Se preserva el comportamiento exacto del negocio y se mantiene la integridad a nivel de BD.

### 4.2 Auditoría y deduplicación previas al ETL (antes de imponer cualquier unique)

El plan dice en F6 *"201.000 registros migrados con discrepancia de conciliación = 0"*, pero la BD actual no tiene **ningún** unique: `placa` tiene cardinalidad 1.258 en 1.246 filas (duplicados casi seguros) y las salidas pueden tener (vehículo-día) repetidos.

**Mejora aplicada:** F6 queda **bloqueado** hasta una auditoría de solo lectura (duplicados de placa, cédulas, salidas vivas duplicadas, JSON inválido, fechas cero, estados fuera de catálogo). Los constraints se crean solo donde los datos lo permitan; el resto se refuerza en la capa de servicio.

### 4.3 Área de la salida nullable (solo por carga histórica)

`Salida.area` como FK NOT NULL + PROTECT rompería el ETL: en legacy el área vive dentro del JSON `datos` y puede faltar en filas antiguas.

**Mejora aplicada:** `area` nullable; la regla real ("área obligatoria cuando la salida es 'disponible'"; "área/carpeta de la persona obligatoria cuando no lo es" — verificado en `transporte_salida.php` 461–477) se valida en `registrar_salida()`, que es donde debe vivir.

### 4.4 Modelos completados y "nada se pierde" como criterio de corte

- De 5 modelos del plan a **~16**, cada uno justificado por una funcionalidad o tabla verificada.
- Las ~20 columnas del vehículo que el modelo 2026 no menciona (vin, motor, kilometraje, sistemas, siniestros, tarjeta de operación, ciudad de operación...) tienen destino documentado, y `como_cond` queda como candidata a eliminación **previa verificación de uso** (regla: nada se elimina sin confirmar).
- Se añade la matriz de trazabilidad funcional: **no se puede ejecutar el cutover sin las 33 filas verificadas**.

### 4.5 Permisos de frontend a permisos de backend

El plan 2026 habla de jefes validadores pero no menciona las **6+ cédulas y flags hardcodeados en el JS/PHP** que hoy deciden quién puede qué (incluida la bifurcación `_fix` de la pestaña Datos). El backend absorbe todas esas decisiones en `PermisoService` + `JefeValidador` + grupos: elimina por completo el "acceso por cédula" del legado.

### 4.6 Dependencias externas visibles, no ocultas

El JS del backoffice consume un **controlador fuera del módulo** (`gerencia_informes_vehiculos_controlador` → `get_vehiculos_transp`), helpers globales (`jsonAllPer` con todo el personal, `loadMapAreasCarpetas`, `saveValidTrans`...) y escribe en una **base de datos externa** (Nokia, en `asignar_movil`). Todo eso queda como endpoints internos equivalentes (E1–E3) y como decisión explícita pendiente (D-A9: ¿cuál es la fuente de verdad de la placa del móvil?).

### 4.7 Lo que se respeta sin tocar

La estrategia de corte único con PHP intacto, la separación conductor externo/empleado, el snapshot de `valor_dia`, el semáforo calculado en servidor (regla verificada idéntica al código), los consecutivos atómicos y el patrón de servicios: **son correctos y se adoptan tal cual**.

---

## 5. Estado de madurez y siguiente paso inmediato

| Bloque | Estado |
|---|---|
| Funcionalidad del módulo (qué hay que reconstruir) | **Verificada al 100% sobre el código disponible** |
| Especificación de backend (modelos, servicios, endpoints, ETL) | **Completa** (`PLAN_BACKEND_DJANGO_CONSOLIDADO`) |
| Reglas de negocio críticas (ventana, anticolisión, novedades, cierres, jefes) | **Verificadas con evidencia en línea de código** |
| Archivos del módulo no disponibles (informes, datos_fix, planilla, reporte fotográfico, controller, JS global) | **Pendientes** — bloquean F3/F5 y el cierre de esas secciones |
| Auditoría de duplicados en BD | **Pendiente** — bloquea F6 y la confirmación finales de constraints |
| Decisiones de entorno (motor destino MySQL vs PostgreSQL, fuente de verdad de la base negra) | **Pendientes de concertar** — bloquean F1 |

**Conclusión:** se cuenta con lo suficiente para iniciar **F0 y F1** con riesgo bajo (diccionario cerrado, esquema y servicios especificados, reglas verificadas). Lo que falta son archivos concretos del sistema y dos decisiones de entorno; ninguno afecta la arquitectura propuesta, solo puede añadir alcance a las fases F3/F5. La regla rectora de todo el plan sigue siendo: **migración funcional, nada se pierde, corte único con el PHP como respaldo**.

---

*Documento de exposición. Ningún archivo del sistema actual fue modificado. Complementa: `PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md` (arquitectura/cronograma), `PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md` (especificación técnica completa), `PLAN_MIGRACION.md` §1.5 (inventario funcional).*
