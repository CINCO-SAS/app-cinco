# Ruta pendiente — Módulo Transporte

> Documento vivo de seguimiento. Los `.md` de `MIGRACIONES/` son la
> **especificación**; éste solo registra **qué falta, en qué orden y qué lo
> desbloquea**. Actualizar la §6 al cerrar cada hito.
> Última actualización: 2026-10-23 · Rama: `feat/modulo_transporte` · Commits locales sin push.

---

## 0. Estado actual (snapshot)

| Fase | Contenido | Avance |
|---|---|---|
| F0 Diccionario y mapeo FKs | Mapeo aplicado en los modelos | ~90% (auditorías CR-3 pendientes → C2) |
| F1 Base Django y Festivos | 16 modelos + migración; **algoritmo de festivos portado + caché** y **catálogo JSON editable** (`apps/common/festivos/`, compartido con otros módulos); falta la tabla `common.Festivo` | ~85% (solo falta la tabla → G1; migrate real → C1) |
| F2 Flota y Conductores | CRUD + semáforo + documentos + CSV (CR-13) + QR (D-A8) + **ficha de contacto del conductor (A1: 3 fuentes, Nokia degradado → G2)** + **licencias y cilindraje recuperados (hueco del legacy)** | ~95% (falta T6 → C3; línea corporativa → G2) |
| F3 Kiosco y Fotos | Núcleo **CERRADO** (B2): alta de salidas S6, consulta B1, escaneo S1; **fotos B3 núcleo cerrado** (ventana/agenda/imágenes en servidor); **kiosco S3 (pre-chequeo) y S4 (consulta por placa) cerrados**; pendiente solo S2 (gated G4) y refinamientos B3 | ~70% |
| F4 Backoffice y Novedades | Backoffice **CERRADO** (B4): `aprobar-lote`, `aprobar`, `rechazar`, `validar`, `DELETE`, novedades (B6/B7), historial y `/validaciones/` (cierre por área); **B11 cerrado** (centro de costos por (carpeta, área) desde `infraestructura_parametros`) | ~95% (código completo; validación contra datos reales → C4) |
| F5 Liquidaciones e Informes | **F5-1…F5-7 CERRADOS** (cuenta de cobro, gráfico, informe mensual, export, WFM + worker, planillas con **formato físico F-104**, agregados de sábana) + **refinamiento F5-2** (área vacía → serie `SIN AREA`, entidades HTML deshechas) | **100%** |
| F6 ETL histórico | Esqueleto cerrado (A3); corrida real → C3 | ~40% |
| F7 Cutover | — | 0% |
| F8 Estabilización | — | 0% |

- 465 tests OK (`config.settings_test_transporte`, SQLite aislado de otros módulos), verificados el 23-oct.
- Contra MySQL real (`default` = `db_cincosas` y `azul`): **C1 (migraciones 0001–0008) y C2 (auditorías) ejecutados el 20-oct**; falta la ETL real (C3) y la validación (C4).

---

## 1. Gates (bloqueadores externos)

| ID | Condición | Desbloquea | Estado / responsable |
|---|---|---|---|
| **G1** | Decisión de negocio: fuente y modelo del calendario de festivos (`common.Festivo`) | B1 (F3); **B2, B3 y B4 cerrados sin G1** con el algoritmo portado | **Desactivado en la práctica (19-oct):** `es_festivo` = algoritmo ∪ catálogo JSON editable (`apps/common/festivos/`); la tabla BD solo añadiría decretar en caliente sin redeploy |
| **G2** | Conectividad: BD `azul` (`192.168.79.10`), BD negra Nokia y `default` | C1–C4, T6 teléfonos | **ABIERTO desde el 20-oct** (C1 migrate real y C2 auditorías ya ejecutados). **Alias `negra` RESUELTO en código** (`e90dd84`): está en `DATABASES` con las variables `DB_NEGRA_*`, el router bloquea sus migraciones y `nokia.py` ya la consulta. **Pendiente (operativo):** apuntar `DB_NEGRA_*` al servidor real en producción + prueba de conectividad y C4 (query de líneas por cédula con datos reales); C3 (carga real del ETL). ⚠️ `sql_mode` **vacío** en `default` y `azul` → sin `STRICT_TRANS_TABLES` MySQL trunca en silencio: habilitar **antes de C3** |
| **G3** | Modelo `common.Area` (viene de otro PHP) | FK de áreas en parámetros/backoffice; B11 (área–carpeta con centro de costos) | **RESUELTO SIN `common.Area` (22-oct):** B11 se cerró leyendo `infraestructura_parametros` directamente (`managed=False`, solo lectura, 94,1 % exacto). Lo único que queda es **código opcional y sin gate**: modelo `common.Area` + CRUD para convertir los 4 snapshots `area` en FK (los `TODO` de `models/salida.py` y `models/liquidacion.py`). No bloquea nada. |
| **G4** | Decisiones **D-A9** (asignar móvil vía outbox asíncrono) y **D-A10** (router BD negra) — §8 | S2 asignar móvil, T6 | Pendientes de decisión técnica |

---

## 2. Tramos

### Tramo A — sin bloqueos (ejecutable hoy)

- [x] **A1 · Parámetros (§5.8)** — ✅ **CERRADO** (`58889b8`, 87 tests).
      CRUD `FechaLimiteCierre` (cierres, unicidad (mes, anio)) y
      `JefeValidador` (áreas/carpetas como JSON → **no exige G3**).
      Endpoints canónicos `/parametros/cierres/` (absorbe B2) y
      `/parametros/jefes/` (D1) + `POST {id}/inactivar/`.
      > **Empleado (managed=False, cross-DB) resuelto:** resolución en dos
      > pasos (cédula→id, luego filtro local `empleado_id`; **cero JOINs**,
      > D-A10) + tabla de prueba creada con `schema_editor` únicamente en
      > tests de transporte. Escrituras con `DjangoModelPermissions`
      > (gate `$permi_editar`; permiso granular `editar_tras_cierre` → E3).
- [x] **A2 · Núcleo de liquidaciones F5 con fixtures** — ✅ **CERRADO**
      (`7a4d89c`, 105 tests). `LiquidacionService`: sábanas CR-10
      (pago mensual APROBADO+REPORTADO+VALIDADO vs pronto pago **solo
      APROBADO**) con retroceso de 6 meses solo si el pedido es el mes en
      curso (legacy 331–348/411–428), `proximo_consecutivo` atómico
      (`select_for_update` + unique, arranque 1000 = MAX global como el
      legacy), `puede_editar_periodo` (gate `editar_tras_cierre`) y upsert
      de `PagoVehiculoMensual` con `total_liquidado` autocalculado (§5.1).
      Endpoints: `GET /liquidaciones/?mes=&anio=` (D3; la ruta compuesta
      `/{anio}/{mes}/` queda como query param — DefaultRouter reserva
      `/{pk}/`), `GET .../pago-mensual|pronto-pago/` (D4),
      `POST .../consecutivo|pago/`. Matemática de períodos extraída a
      `services/periodos.py` (fuente única con cierres). *Pendiente de A2:
      ruta compuesta B3 `/cierres/{mes}/{anio}/`; planilla/informes van
      tras B2.*
- [x] **A3 · Esqueleto del comando ETL con fixtures locales** — CERRADO.
      `apps/transporte/etl/` (normalizadores D-A4/D-A6, convertidores puros
      §7.2, carga con FKs por cédula/placa + lotes + conciliación) y
      `manage.py migrate_transporte_legacy` (`--fuente/--lote/--dry-run`);
      muestras en `etl/muestras/`. La validación real recién en C3 (G2).
      *Hallazgo: la conciliación usa `convertidas` (no creadas): una fila
      que convierte pero falla al cargar descuadra y el comando sale con
      estado 1 — intencional, el cutover no avanza con datos perdidos.*

> T6 (teléfonos/`buscar_movil`) **no** es Tramo A: encadena tres BD (G2) y arrastra D-A9/D-A10 (G4).

### Tramo B — requiere G1 (festivos) · B1 ya operativo (solo falta la tabla opcional)

- [ ] **B1 · F1-resto: festivos** — modelo/precarga del calendario + caché en memoria
      + tests de la regla de −2 días hábiles (CR-9). *Tamaño M · Es gate de todo el tramo.*
      **Avance (19-oct): B1 DE FACTO OPERATIVO.** El calendario vive en
      **`apps/common/festivos/`** (módulo reutilizable por cualquier app) con dos
      fuentes: el ALGORITMO (18 festivos estatutarios Ley 51/1983 + Pascua
      Butcher/Meeus, port de `frontend/src/utils/festivos/festivosColombia.ts`) y
      el **catálogo editable `festivos_colombia.json`** (2022–2030, con el feriado
      decretado 2026-07-13). `es_festivo` = **algoritmo ∪ catálogo**: agregar un
      festivo = editar el JSON y `recargar_catalogo()` (sin código, sin migración);
      validado por tests contra el algoritmo (así se detectó y corrigió el
      2027-06-28 → 2027-07-05 del archivo de origen).
      G1 ahora solo gatea la TABLA `common.Festivo` (opcional): al llegar,
      `es_festivo` = algoritmo ∪ catálogo ∪ BD.
      **Paridad verificada:** el legacy CR-9 excluía sábados
      (`base_salida_transporte.php` 77–96) → la ventana usará
      `sabado_habil=False` explícito.
- [x] **B2 · F3 núcleo: registro de salidas** — ✅ **CERRADO** (`cffd8f8`, 162 tests).
      `SalidaService`: ventana CR-9 con `calendario` (−2 días hábiles,
      sábados NO hábiles; bypass programación/admin y jefe del área,
      mensajes legacy literales), anticolisión CR-1 `(vehículo, fecha)` y
      CR-2 `(conductor, fecha)` excluyendo `ELIMINADO` (liberados por
      borrado lógico), snapshots `area/carpeta/sede/valor_dia`,
      exigencia estricta de personal / área manual en "disponible",
      máquina de estados `REPORTADO → APROBADO/RECHAZADO/ELIMINADO` y
      `APROBADO → VALIDADO` (D-A11; `RECHAZADO` terminal) con
      `SalidaHistorial` por fila + `AuditoriaLog`. Endpoints:
      `GET/POST /salidas/`, `GET /salidas/{id}/` (S6/B1) y
      `POST /kiosco/escanear/` (S1: QR D-A8 → placa + salida del día).
      Las transiciones vía HTTP (aprobar-lote/rechazar/validar/DELETE) y
      las novedades quedan para B4 — el servicio ya lo soporta.
- [x] **B3 · F3 reporte fotográfico (núcleo)** — ✅ ventana 10:00–16:00 y gate de
      agenda (`operaciones_agenda`, **solo lectura de módulo ajeno**) validados
      EN SERVIDOR; exención de área (`transporteOmiteValidacionOt`); 1–5 imágenes
      con compresión Pillow; dedup `(vehículo, fecha, técnico)`; identidad desde
      `request.user` (no del cliente). Endpoints: `POST /reportes-fotograficos/`,
      `POST .../validar-agenda/`, `GET .../vehiculo-placa/`. **Núcleo CERRADO**
      (214 tests). **Refinamiento #1 CERRADO (20-oct): match OT-específica**
      `validar_agenda_ot` (port del `controlador_fix` 319–360 y 175–244): la
      OT declarada debe coincidir exactamente —mayúsculas y espacios
      colapsados— con `actividad.ot`, `tipo_trabajo`, `descripcion` u
      `observacion` de una agenda no borrada del día. Aplicado en `guardar()`
      y en el pre-chequeo `validar-agenda/`; áreas exentas y WFM/IM intactas,
      y sin OT declarada no se endurece el gate ya cerrado.
      *Pendiente (diferido):* ventana de días anteriores con excepción en
      `programacion_parametros` (→ decisión de diseño: storage propio + CRUD
      con `puede_programar` + ETL de las excepciones).
- [x] **B4 · F4 backoffice** — aprobación masiva, rechazo con motivo, eliminación
      lógica, novedades, historial (`SalidaHistorial`) y validación de jefes
      (`ValidacionSalida`, con datos de A1). *Tamaño M.* **CERRADO** (182 tests).

### Tramo C — G2 ABIERTO el 20-oct

- [x] **C1 · Migrate real** — ✅ **CERRADO (20-oct)**: `0001`–`0006` aplicados contra
      `default` = **`db_cincosas`** (MySQL 8.0.46). **17 tablas `transporte_*`** creadas
      vacías (utf8mb4_unicode_ci ✓) + **79 permisos** activos (incluidos los custom
      CR-8: `puede_programar`, `permiso_especial`, `editar_tras_cierre`). Ninguna de
      las 50 tablas pre-existentes fue tocada. Herramientas: `inspeccion_bd_legacy`
      y `auditar_datos_legacy` (ambas de **solo lectura**).
      *⚠️ `mysql.W002`: `sql_mode` **vacío** en `default` y `azul` → sin
      `STRICT_TRANS_TABLES`; MySQL trunca silenciosamente. Habilitarlo antes de C3.*
- [x] **C2 · Auditorías §7.1** — ✅ **INFORME listo (20-oct)**, solo lectura sobre
      `azul` (`manage.py auditar_datos_legacy`). Espejo real:
      - **CR-3 placas** — 1.307 vehículos / 1.304 placas distintas; **3 duplicadas**:
        `MXW46F` (ids 1822,1825) · `TSG407` (730,870) · `TTP822` (826,1192). Cédulas de
        conductor: **1 duplicada** (`10235098`). Cédulas de personal: **0** ✓ → el
        UNIQUE de `placa`/`cedula` es viable tras resolver esos 4 casos puntuales.
      - **CR-1 (vehículo, día) con estado vivo: 303 colisiones** (620 filas, máx. 5/día):
        **256 son duplicados técnicos** (mismo timestamp/técnico/móvil → doble submit
        del PHP) y **47 son salidas múltiples reales**. Por año 2022:135 · 2023:107 ·
        2024:58 · **2025:3**; solo **2 en los últimos 12 meses**.
      - **CR-2 (móvil, día) NO es viable**: `movil_sale` **nunca es placa** (0/253.035)
        sino el móvil nombrado (`TIRAN119`, `MOVIL 11`, `HW-CONSTRU`…), con ~70k
        sentinelas (`Z - FUERA` 42.260 · `Z - FUERA DE OPERACION` 16.711 ·
        `disponible` 7.938 · `0` 1.392 · `1 - SIN ASIGNAR` 1.273) y móviles comunes
        asignados a 14 personas el mismo día **por diseño**.
      - **Huérfanos**: 60 vehículos borrados (~700 salidas) · 148 técnicos sin personal
        (el `0` con 17.192 salidas) · 3.427 sin móvil · **488 filas en estado
        `disponible`** (estado no estándar). Rango: 2021-10-06 → 2026-10-31.
      - **Conclusión D-A12**: los datos legacy **no permiten** los constraints parciales
        CR-1/CR-2 tal como estaban previstos; el criterio se refuerza en
        `SalidaService` (ya implementado). *La importación de datos la ejecuta el
        usuario; el backend no escribe en `azul`.*
- [ ] **C3 · F6 ETL** — `manage.py migrate_transporte_legacy`: lotes de 2.000,
      desempaquetado del JSON `datos`, resolución de FKs (`ID Foreign Keys`),
      **jefes** (`programacion_parametros`), **fechas límite**, **festivos** (si su
      fuente es PHP) y **T6 teléfonos** (cascada azul→negra).
      *DoD: 201.000 registros con conciliación = 0.*
- [ ] **C4 · Validación contra datos reales** — semáforos SOAT/CDA, upserts de
      bancarios y QR sobre datos de producción (solo lectura).

### Tramo D — cierre

- [ ] **D1 · F7 cutover único** — dry-run en pruebas, ventana de congelación de
      escrituras legacy, sincronización final, pase de puntero `ConfigMenu`
      (rollback < 2 min) y E2E completo. *PHP intacto como respaldo.*
- [ ] **D2 · F8 estabilización** — índices/monitoreo en MySQL, archivo del PHP
      legacy, informe final del proyecto.

### F5 — desglose en curso (Tab 2 informes + planillas)

Núcleo de liquidaciones **CERRADO** en A2 (D3/D4, CR-10, consecutivos). El
resto de F5, troceado de menor a mayor (1 hito = 1 commit). WFM y cuenta de
cobro no tienen fila propia en la matriz §6: viven dentro de la sábana (I1).

- [x] **F5-1 · Cuenta de cobro** — ✅ `GET /informes/cuenta-cobro/?placa=&mes=&anio=`
      devuelve HTML imprimible (legacy `cuenta_cobro_plantilla.php`).
      **Mejora de integridad:** el legacy imprimía `pagar`/`banco`/`cuenta`/
      `nombre` desde campos ocultos del formulario (importe alterable desde
      el navegador); aquí el importe se calcula en SERVIDOR
      (`valor_base = Σ total_a_pagar`; retefuente 1 %; `pagar = base − rete`)
      y el pagador se lee de `DatosBancariosVehiculo` (fallback: propietario).
      Consecutivo tomado de `ConsecutivoMensual` si existe. *Tamaño S.*
- [x] **F5-2 · Gráfico mensual por área** — ✅ `GET /informes/series-chart/?anio=`
      devuelve `{"series": ...}` para el gráfico "Pagos por Mes, por Área"
      (suma de `total_a_pagar` por (área, mes); I&M al eje secundario a2 con
      su estilo). **Corrección del bug legacy:** el PHP recibía `mes`/`yyyy`
      y hacía `execute([2024])` — fijaba 2024 a mano e ignoraba ambos; el año
      ahora es un filtro opcional **respetado** (sin año: histórico completo).
      Estados como el legacy post-01/08/2024 (VALIDADO + APROBADO).
      **Refinamiento (23-oct, `266341b`):** el área vacía entra como serie
      `SIN AREA` (el PHP la omitía con `continue` y el total no cuadraba con
      Transporte Mes) y `_area_de` deshace entidades HTML (`E&amp;N` → `E&N`).
      *Tamaño S.*
- [x] **F5-3 · Informe mensual + filtros** — ✅ `GET /informes/mensual/?mes=&anio=&estado=&sede=&area=&carpeta=&search=`
      (§5.7 `InformeService.mensual`): salidas **no eliminadas** del mes,
      filtros server-side, orden **día a día** (ascendente), paginado, con
      `SalidaSerializer` (placa, área, valor día, novedad, `total_a_pagar`,
      `puede_gestionar` B15). + `GET /informes/areas/?mes=&anio=` (áreas del
      periodo → `arr_areas` de la sábana). Rango de mes **semiabierto**
      `[desde, hasta)` como `LiquidacionService` (no `__range`, que incluye
      el día 1 del mes siguiente). *Tamaño M.*
      **Hallazgo (corregido):** no existía `DEFAULT_PAGINATION_CLASS` en el
      proyecto, así que `get_paginated_response` daba **HTTP 500** en
      `GET /salidas/` (B1/B4) — latente porque los tests iban a nivel
      servicio. Creado `views/paginacion.py` (`PaginacionTransporte`) y
      aplicado a `SalidaViewSet` e `InformeViewSet`.
- [x] **F5-4 · Export server-side CERRADO** — fila B4: `GET /salidas/export/?formato=xlsx|csv`
      (migrado de client-side DataTables a server-side). Reutiliza
      `SalidaService.listar` (mismos filtros B1) + `InformeService.exportar`
      (13 columnas de la sábana, números reales en XLSX; CSV `;` + BOM
      utf-8 para Excel español). `openpyxl==3.1.5` declarado en
      `requirements.txt`.
      ⚠️ El parámetro se llama `formato`, **no** `format`: DRF reserva
      `format` para su content negotiation (`?format=`) y lo convertía en
      **404**.
- [x] **F5-5 · WFM** — ✅ **CERRADO** (330 tests). `WfmService` (§5.10): ventana
      de 2 días hábiles, elegibilidad WFM primaria + agenda como respaldo
      (hallazgo: los mapas "completado"/"any" del legacy eran idénticos),
      lote síncrono con `select_for_update` (el UPDATE a ciegas del
      legacy permitía carreras) y cola de jobs idempotente por chunk
      (`chunkDays=1`). Transición `REPORTADO → VALIDADO` incorporada a
      `TRANSICIONES` (D-A11 extendido con evidencia legacy 426–445).
      Endpoints: `POST /wfm/validar/`, `/wfm/crear-job/`, `/wfm/estado-job/`
      (con respaldo síncrono). **Worker**: `manage.py wfm_worker`
      (port de `transporte_validacion_wfm_worker.php`: `reclamar_siguiente`
      con precedencia PROCESANDO-huérfano, 1 chunk por defecto,
      `--hasta-completar` / `--job <uuid>`; cron sugerido cada 5 min).
- [x] **F5-6 · Planillas** — ✅ **CERRADO** (330 tests). `POST /planillas/generar/`
      (S5, CR-11): alcances PLACA/PROPIO/EXTERNO/RENTING/TODAS,
      **filtro duro `tipo != 'MOTO'` explícito en todos los alcances**
      (legacy `transporte_salida.php` 597/608/663; los choices no bastan
      contra datos legacy de la ETL), consecutivo atómico por vehículo y
      QR en disco. Permisos: exige `add_consecutivomensual` (generar
      planilla ESCRIBE consecutivos). **P1 CERRADO (19-oct):** verificado
      `planilla_salida.php` y **formato físico F-104 implementado** en
      `POST /planillas/formato/` (HTML autocontenido LETTER horizontal, una
      hoja por vehículo, QR en base64, casillas en blanco para firmas de
      salida/retorno). Mejoras sobre el legacy: FECHA real (imprimía
      "16/02/2022" fijo), CONDUCTOR/TELÉFONO y VALOR DÍA reales (la consulta
      del legacy estaba *comentada* y salían vacíos), CONSECUTIVO impreso
      (PLAN_TECNICO §3.6 lo exige y el formato no lo mostraba) y sin código
      de barras (D-A8 lo eliminó como artefacto regenerable).
- [x] **F5-7 · Agregados de sábana** — ✅ **CERRADO** (355 tests). Agregaciones
      server-side del JS de la sábana (`transporte_salida_informes.php`):
      `GET /informes/dia/?fecha=` (día → área → carpetas con `arr_estado`),
      `GET /informes/area/?mes=&anio=&solo_aprobados=` (totales del mes,
      interruptor "solo aprobados" = APROBADO/VALIDADO),
      `GET /informes/areas-mes/?anio=` (matriz área × meses),
      `GET /informes/nomina/?mes=&anio=` ((carpeta, placa), rete 1 %,
      pagador en servidor CR-13; **`centro_costo` vacío hasta G3/B11** —
      el legacy lo tomaba de `map_carpetas` en JS) y
      `GET /informes/liquidacion/?mes=&anio=` (por placa, rete 1 %,
      consecutivo). REPORTADO/ELIMINADO excluidos en nómina y liquidación.
      *Mejorado vs. legacy (no se replican sus rarezas):* claves de
      estado con el nombre real (`reportado`, `total`; el legacy decía
      `pendiente`/`total_est`), RENTING contado **aparte** de PROPIO (el
      legacy lo metía en `propios`) e importes en `Decimal` con 2
      decimales (el legacy los truncaba a entero con `parseInt`).
      *El "pronto pago" ya existía en A2 (`/liquidaciones/pronto-pago/`).*

### Frontend — estado y pendiente (23-oct)

5 pantallas operativas (Salidas, Reporte Fotográfico, Flota, Conductores,
Informes), sin datos mock: todo pasa por `transporte.service.ts`. **~30
endpoints del backend ya definidos en el servicio y sin consumir.**

- [x] **Informes — PASOS 2 a 7 COMPLETOS (23-oct): la sábana del Tab 2
      está migrada al 100 %** y ya no queda ningún `BloquePendiente`.
      Paso 5 "Día a Día" (`4560643`: `/informes/mensual/` como listado
      paginado con filtros server-side) · Paso 6 "Área y Carpeta"
      (`f6a9af4`: matriz área × meses) · export de "Transporte Mes"
      (`fbae935`: `GET /salidas/export/` con el rango del mes; XLSX y CSV)
      · Paso 7 cierre del mes (`35c5066`: nómina por (carpeta, placa),
      liquidación por vehículo y cuenta de cobro imprimible que se abre en
      pestaña nueva desde el HTML del servidor).
- [ ] **Informes — botones sin cablear:** Excel de "Reporte Área" y
      refresco WFM del área I&M (⚠️ `/wfm/validar/` **escribe**
      validaciones: requiere permiso y confirmación explícita).
- [ ] **Pantallas sin crear** (`disponible: false` en `transporteModulos.ts`):
      `kiosco`, `liquidaciones`, `planillas`.
- [ ] Flota es solo consulta (sin CRUD ni ficha); en Salidas no hay botón de
      exportación (el de Informes ya existe).

---

## 3. Orden recomendado

```
   LISTO (código completo, sin gates)          G2 (BD)                 CIERRE
 ┌─────────────────────────────┐          ┌──────────────────┐    ┌──────────┐
 │ Tramo A: A1 A2 A3           │          │ C1 migrate real  │    │ D1 F7    │
 │ Tramo B: B1 B2 B3 B4        │ ───────► │ C2 auditorías    │ ─► │ D2 F8    │
 │   (festivos: algoritmo ∪    │          │ C3 ETL  C4 real  │    └──────────┘
 │    catálogo JSON, sin G1)   │          └──────────────────┘
 │ F5-1…F5-7 · CR-8 cerrados   │
 └─────────────────────────────┘
   Gates restantes (todo gated, ninguno bloquea el resto): G3 (common.Area → B11)
   · G4 (outbox D-A9/D-A10 → S2/T6) · G1 solo aportaría la tabla BD opcional
   para decretar festivos en caliente. P1 (formato físico) CERRADO el 19-oct.
```

**Recomendación:** no queda trabajo de backend sin gate. Lo único que mueve la
aguja ahora es **G2** (conectividad a BD → Tramo C completo con datos reales);
G3 y G4 desbloquean los últimos dos puntos sueltos (B11 y S2/T6).
---

## 4. Riesgos

| ID | Riesgo | Mitigación |
|---|---|---|
| R1 | Lógica escrita sin datos reales (G2 cerrado) | Fixtures desde specs + ejecución temprana de C1 apenas haya conectividad |
| R2 | A2 (F5) adelantado a B2 (F3) → posible rework | Specs CR-10/D-A11 cerradas; mover A2 tras B2 si se prefiere orden estricto |
| R3 | Dependencia de módulos ajenos (`operaciones_agenda`, `cinco_base_de_personal`, Nokia) | **Solo lectura**; nunca editar otros módulos (regla del proyecto) |
| R4 | Regresión en otros módulos | Tests aislados (`settings_test_transporte`) + `manage.py check` en cada hito |
| R5 | Divergencia con el PHP legacy | Legacy intocado; cualquier cambio de regla es decisión de negocio documentada |

---

## 5. DoD estándar de cada hito

1. Tests en verde: `backend\.venv\Scripts\python.exe backend\manage.py test apps.transporte --settings=config.settings_test_transporte`
   *(el venv canónico es `backend/.venv` — `backend/README.md`; el `.venv` de la raíz se eliminó el 19-oct por estar roto: apuntaba a un Python 3.14 inexistente)*
2. `backend\.venv\Scripts\python.exe backend\manage.py check` sin issues
3. Commit local (**sin push**)
4. Marcar el hito en la §6 y actualizar la fecha de este documento

---

## 6. Registro de avance

| Fecha | Hito | Commit |
|---|---|---|
| 2026-10-14 | F0/F1-base: modelos, config, migración inicial | `313ec7a` |
| 2026-10-14 | F2 conductores completo | `ca7f522` |
| 2026-10-14 | F2 flota completo (semáforo, documentos) | `8eaa38a` |
| 2026-10-14 | Fix tests MEDIA_ROOT temporal | `f88221c` |
| 2026-10-14 | Import CSV bancarios (CR-13) | `5fd3583` |
| 2026-10-14 | QR bajo demanda (D-A8) + dependencias | `c97b9bb` |
| 2026-10-14 | ROADMAP: tramos, gates y orden pendiente | `35f2186` |
| 2026-10-14 | A1 parámetros completo: cierres + jefes (87 tests) | `58889b8` |
| 2026-10-14 | A2 núcleo liquidaciones: CR-10, consecutivos, gate (105 tests) | `7a4d89c` |
| 2026-10-14 | A3 esqueleto ETL: comando + muestras + conciliación (126 tests) — **Tramo A completo** | `3c8a457` |
| 2026-10-15 | Calendario de festivos portado del frontend (18 festivos, CR-9 desbloqueada) | `59c80dd` |
| 2026-10-15 | B2 núcleo de salidas: CR-9/CR-1/CR-2, D-A11, /salidas/ + /kiosco (162 tests) | `cffd8f8` |
| 2026-10-15 | B4 backoffice F4: novedades, historial, perfil gestión, /validaciones/ (182 tests) | `a652fc0` |
| 2026-10-15 | B3 reporte fotográfico (núcleo): ventana/agenda en servidor, imágenes Pillow, /reportes-fotograficos/ (214 tests) | `d510271` |
| 2026-10-15 | Kiosco S3/S4: pre-chequeo /kiosco/validar/ (CR-9/CR-1/CR-2) y consulta /kiosco/vehiculo/{placa}/ (225 tests) | `bac53fe` |
| 2026-10-15 | F5-1 cuenta de cobro: /informes/cuenta-cobro/ HTML imprimible, importe y pagador en servidor (238 tests) | `ec9b2db` |
| 2026-10-15 | F5-2 gráfico por área: /informes/series-chart/ corrige el hardcode 2024 del legacy; año como filtro (246 tests) | `eb2656f` |
| 2026-10-15 | F5-3 informe mensual: /informes/mensual/ + /areas/ con filtros server-side; fix paginación (500 latente en /salidas/) (255 tests) | `7f0f362` |
| 2026-10-15 | F5-4 export server-side: /salidas/export/?formato=xlsx|csv, 13 columnas, mismos filtros B1 (260 tests) | `3013df2` |
| 2026-10-19 | F5-5 WFM + F5-6 planillas: cola+lote WFM con worker y planilla oficial con consecutivo y QR (330 tests) | `6c2e10c` |
| 2026-10-19 | Hallazgos de calidad: permisos de modelo en /planillas/, tecnico_cedula real, filtro duro MOTO (CR-11), worker `wfm_worker`, .venv raíz roto eliminado (339 tests) | `33e8d7e` |
| 2026-10-19 | F5-7 agregados de sábana: /informes/dia, /area, /areas-mes, /nomina y /liquidacion server-side (351 tests) | `c39ee9a` |
| 2026-10-19 | Revisión de cambios subidos: registro real de `/validaciones/` (desde B4 el ViewSet existía pero la ruta devolvía 404), `serializer_class` en cierres/jefes (500 latente en GET), fix clave duplicada `tipo_vinculacion` en ETL de conductores, paginación canónica en 6 listados, inline de datos bancarios en admin (353 tests) | `91615d4` |
| 2026-10-19 | Refactor F5-7 (mejora sobre el legacy): claves de estado reales (`reportado`/`total`), RENTING separado de PROPIO, importes en `Decimal` con 2 decimales (355 tests) | `76c140f` |
| 2026-10-19 | E1 catálogo operativo + E3 PermisoService (cierra CR-8): `/vehiculos/catalogo-operativo/` (solo activos, semáforo en servidor) y `/permisos/estado/` (grupos/permisos en vez de cédulas hardcodeadas, migración 0006) (365 tests) | `65c2709` |
| 2026-10-19 | Calendario reutilizable (G1 parcial): `apps/common/festivos/` con el algoritmo + catálogo editable `festivos_colombia.json` (2022–2030, feriado decretado 2026-07-13 incluido); `es_festivo` = algoritmo ∪ catálogo (agregar festivo = editar JSON y `recargar_catalogo()`, sin código ni migración); transporte queda como shim sin cambio de comportamiento; corrección del JSON de origen: San Pedro y San Pablo 2027 estaba en el lunes anterior (2027-06-28) → 2027-07-05 según Emiliani; +10 tests en `apps.common` (377 tests) | `6f3e837` |
| 2026-10-19 | P1 CERRADO: formato físico F-104 en `POST /planillas/formato/` verificado contra `planilla_salida.php` (LETTER horizontal, hoja por vehículo, QR en base64, casillas en blanco para firmas); mejora sobre el legacy: fecha real (el legacy imprimía 16/02/2022 fijo), conductor/teléfono/valor día reales (la consulta del legacy estaba comentada), consecutivo impreso (§3.6) y sin código de barras (D-A8); +12 tests (389 tests) | `7e00e26` |
| 2026-10-20 | Refinamiento B3 #1 CERRADO: match OT-específica `validar_agenda_ot` portado del `controlador_fix` (la OT declarada debe coincidir exactamente con `actividad.ot`/`tipo_trabajo`/`descripcion`/`observacion` de una agenda no borrada del día); aplicado en `guardar()` y en `validar-agenda/`; áreas exentas y WFM/IM intactas; el #2 (ventana de días anteriores con excepción) queda pendiente de decisión de diseño | `c61e5be` |
| 2026-10-21 | **A1 ficha de contacto del conductor** (cierra la última acción de `base_transportadores.php` que faltaba): `GET /vehiculos/{id}/contacto/` y `ContactoService`, que cruza las 3 fuentes del legacy (línea corporativa Nokia, celular de `transporte_base_conductores` y los 3 teléfonos de `cinco_base_de_personal`); cross-BD sin JOIN (D-A10) y con degradación explícita de Nokia (`nokia_disponible=false`) mientras no haya gate G2; `linea_corporativa` pasa a ser lista (el `group_concat` legacy devolvía una cadena) | `32a2885` |
| 2026-10-21 | **Huecos del legacy recuperados en flota**: al auditar `base_transportadores.php` contra `DICCIONARIO_DATOS.md` aparecieron 4 columnas que el legacy tenía y Django no. `cilindraje` (varchar 11, "numérico como texto") vuelve al `Vehiculo`; `licencia` (SI/NO/NO APLICA → `posee_licencia`), `estado_licencia` (ACTIVA/INACTIVA → `situacion_licencia`), `categoria` (A1..C3) y `fecha_licencia` vuelven al `Conductor` (de quien son), que era un hueco real: el docstring decía "pertenecen al conductor" pero nunca se habían añadido. **Fix de pérdida de datos:** `CategoriaLicencia` solo tenía 4 de las 8 categorías del legacy, así que la ETL convertía a NULL las licencias A1/A2/B2/B3 → catálogo ampliado a 8. La ETL_enriquece al conductor con la copia del vehículo **solo en campos vacíos** (resultado independiente del orden de carga). El semáforo `estado_licencia` (VIGENTE/POR_VENCER/VENCIDA) NO se toca: el flag manual del legacy va en `situacion_licencia` para que no choquen. Migración 0007 (3 AddField nullable + AlterField de choices), sin migración de datos. **Pendiente:** `migrate` contra la BD real (no ejecutado) | `8dfef71` |
| 2026-10-22 | **B9 ficha del móvil** (el último endpoint de la matriz §6): `GET /personas/{cedula}/ficha-movil/` + `SalidaService.buscar_movil` (plan §5.1). Resuelve QUIÉN es un móvil, qué vehículo tiene ASIGNADO y con qué salida salió hoy. La cascada es la versión normalizada del `movil_sale` legacy (que guardaba en una sola columna valores de tres naturalezas): (1) conductor externo → `Conductor`; (2) personal de nómina → `Empleado` (BD azul); (3) línea corporativa Nokia → `nokia_base_lineas`, **no disponible** (no existe el alias `negra` en `DATABASES`, gate G4/D-A10) → se degrada con `nokia_disponible=false` en vez de dar 500. La consulta a la BD negra vive en **`services/nokia.py`** (compartida con `ContactoService`, sin duplicar SQL), así que al añadir el alias a `settings` la 3ª fuente de la cascada funciona sin tocar nada más. Cross-BD sin JOIN (D-A10): cédula → Empleado y placa → Vehiculo, dos pasos. El vehículo asignado sale de `cinco_base_de_personal.placa`, que es la **segunda fuente de verdad de la placa del móvil** (la primera es la BD negra): deja D-A9 a medias pero comprobable. La "pk" del recurso es la CÉDULA, no un id. La matriz §6 queda con 1 endpoint pendiente (S2, gated G4) y E2 parcial. +13 tests (441 tests) | `4aad3b3` |
| 2026-10-22 | **B11 · área–carpeta con centro de costos** (G3 deja de ser gate: es código): `centro_costos` incluido en `GET /salidas/`. Fuente ÚNICA **`infraestructura_parametros`** (BD azul) — verificado que es la única tabla del legacy con `centro_costo` (`cinco_base_de_personal` no tiene ninguna columna de costo y su JSON `datos` es de RRHH: hijos, vacunación, tallas, contactos). Modelo **`managed=False`** + `save()`/`delete()` que LANZAN `NotSupportedError`: la promesa de solo lectura está **impuesta por el código**, no solo documentada (migración `0008` = estado, sin DDL). **Mejora sobre el legacy:** el PHP no sabía desambiguar las 6 carpetas con dos centros de costos y acumulaba todas en un `Set`, mostrándolas juntas y delegando la decisión a contabilidad; aquí se resuelve con **(carpeta, área)**, que sobre las **146.278 salidas vivas** resuelve **136.589 exactas** y deja **1 sola** ambigua → **94,1 % exacto, 0,0 % ambiguo**, con fallback `"Sin asignar"` literal (`transporte_salida_informes.php:4190`) para el 5,9 % restante. **Dos bugs de presentación corregidos:** el JS imprimía `[23(None)]` cuando faltaba subcentro y `[16([1])]` cuando era array → ahora `[23]` y `[16(1)]`. **1 sola query por request** (catálogo de 90 filas cacheado en el contexto del serializer): un listado de 100 salidas no hace 100. `ParametrosService.centro_costos(carpeta, area, catalogo)`. +19 tests (**462 tests**) | `5168f0c` |
| 2026-10-22 | **Frontend Flota**: los KPIs vuelven, pero fuera de la barra de filtros (separar métrica de criterio de filtro evita que un KPI mutuo active un filtro contradictorio) | `8a7fec1` |
| 2026-10-23 | **Frontend Informes (base)**: tipos y servicios de informes (`transporte.types.ts` / `transporte.service.ts`) + bloques **Día** y **Mes** de la sábana | `36f3205` |
| 2026-10-23 | **Frontend Informes**: bloque **Reporte Área** (matriz área × carpetas) | `73cd6c2` |
| 2026-10-23 | **Frontend Informes**: gráfico **"Pagos por Mes, por Área" (F5-2)** con amCharts 5, consumiendo `GET /informes/series-chart/` | `6d5ff4d` |
| 2026-10-23 | **Refinamiento F5-2 CERRADO**: decisión sobre el legacy — el PHP omitía las salidas sin `area_sale` (`continue`) y el total del gráfico no cuadraba con la tabla de Transporte Mes; ahora entran como serie **`SIN AREA`**. Además `_area_de` deshace entidades HTML: `E&amp;N` (124 filas legacy) se fusiona con `E&N` (12.549), y `I&M`/`E&N` (no son entidades válidas) vuelven idénticos. Agrupado con `_area_de` (normaliza mayúsculas/espacios) en vez del área cruda del legacy. +4 tests (**465 tests**, verificados 23-oct) | `266341b` |
| 2026-10-23 | **Frontend Informes · Paso 5 CERRADO: bloque "Día a Día"** (`4560643`): `/informes/mensual/` (F5-3) como listado paginado con filtros server-side (estado/área/carpeta/sede/búsqueda con debounce) y las columnas de la sábana + centro de costos B11. El badge de estado se mudó a `modules/transporte/components/EstadoSalidaBadge.tsx` (ahora dos pantallas pintan las mismas filas) y el tipo `Salida` ganó `centro_costos`, que el backend llevaba dos hitos devolviendo | `4560643` |
| 2026-10-23 | **Frontend Informes · Paso 6 CERRADO: bloque "Área y Carpeta"** (`f6a9af4`): matriz área × meses de `/informes/areas-mes/` (F5-7) como tabla —fila por área, 12 columnas, TOTAL y pie por mes—, que es la forma tabular del gráfico F5-2. Responde SOLO al año (el endpoint no admite mes ni "Solo aprobados"); celda vacía = «—», no «$ 0» | `f6a9af4` |
| 2026-10-23 | **Frontend Informes · export de "Transporte Mes" cableado** (`fbae935`): botones Excel/CSV en la cabecera del bloque que bajan las salidas del mes vía `GET /salidas/export/` (F5-4) con el rango `desde`/`hasta`. Límite expuesto en la interfaz: el export no entiende «Solo aprobados» (el filtro B1 admite UN estado), así que trae todas las salidas del mes salvo las eliminadas. `InformeBloque` ganó el slot `acciones` | `fbae935` |
| 2026-10-23 | **Frontend Informes · Paso 7 CERRADO — la sábana del Tab 2 queda sin bloques pendientes** (`35c5066`): cierre del mes en tres bloques — **Nómina** (`/informes/nomina/` agrupado por (carpeta, placa)), **Liquidación** (`/informes/liquidacion/`, una fila por vehículo; banco · tipo · número en una sola celda) y **Cuenta de Cobro** (selector de placa tomado de la propia liquidación + pestaña nueva con el HTML del servidor F5-1, abierta ANTES del `await` para no caer en el bloqueo de popups). Nómina y liquidación se piden en paralelo en un mismo hook (mismo mes, dos agrupaciones: no deben divergir); excluyen REPORTADO/ELIMINADO y aplican retefuente 1 %; el pagador llega de los datos bancarios vigentes en servidor (CR-13). `centro_costo` NO se pinta: el backend lo devuelve vacío hasta consumir B11 (deuda C). Se retiró `BloquePendiente` (ya no hay reservas) | `35c5066` |
| 2026-10-23 | **Cierre de huecos en tests HTTP y fix de PATCH en ViewSets**: detectado y corregido bug en `cierre_view.py`, `jefe_view.py`, `conductor_view.py` y `vehiculo_view.py` donde `update` no pasaba `instance` ni `partial=partial` al serializer DRF (los PATCH devolvían 400). Implementada suite `IntegracionHttpEndpointsTests` en `tests.py` con 11 pruebas HTTP de punta a punta (`APIClient`) cubriendo los ~20 endpoints de las 6 vistas (`salida`, `liquidacion`, `cierre`, `jefe`, `conductor`, `vehiculo`). +11 tests (**476 tests OK**, verificados 23-oct) | `local` |
| 2026-10-23 | **Frontend Kiosco de Despacho (S1-S4 CERRADO)**: flujo de 3 pasos en /transporte/operacion/kiosco/ — Paso 1: identificar vehiculo por placa (POST /kiosco/identificar/), Paso 2: confirmar datos de salida (fecha + movil_sale) + pre-chequeo S3 (POST /kiosco/validar/), Paso 3: confirmar y registrar (S6). Stepper visual, manejo de salida existente del dia, badge de validacion con detalle de duplicados CR-1/CR-2, pantalla de exito. Kiosco agregado al sidebar de Operacion. Tipos KioscoDatoVehiculo, KioscoResultadoValidacion, KioscoRespuesta agregados a transporte.types.ts. TS compila sin errores. | local |
| 2026-10-26 | **Cobertura de vistas al 91% + 3 bugs de la capa HTTP corregidos**: suite `IntegracionHttpEndpointsTests` ampliada +7 (alta S6 por HTTP con regla de personal y ventana CR-9 operador-vs-admin, documentos de vehículo con upsert del SOAT, importar-bancarios CSV multipart con y sin archivo, ramas 400/404 de salidas/vehículos/conductores/jefes/cierres y el gate de cierre mensual 403 con y sin `editar_tras_cierre`). **483 tests OK**; cobertura de vistas **85% → 91%** (salida 93, vehículo 92, ninguna vista <85) y del módulo **93%**. Bugs hallados y corregidos: (1) PATCH/PUT a id inexistente devolvía **500** en cierre/jefe/conductor/vehículo (`Service.obtener()` fuera del `try` y el handler global no traduce `ValueError`); (2) `POST /vehiculos/{id}/documentos/` rechazaba SIEMPRE el upload multipart (`{**request.data}` sobre un `QueryDict` extrae el dict interno de `MultiValueDict` → valores como listas); (3) el `UniqueTogetherValidator` automático del serializer bloqueaba el upsert por (vehiculo, tipo) del servicio — la 2ª subida del mismo tipo devolvía 400. Verificado: suite completa SQLite + `tsc` limpio | `e90dd84` |
| 2026-10-26 | **Verificación global del repo (todas las apps, skill django-verification)**: descubiertos **1229 tests** en 7 apps (transporte 483 + ~746 en ia_dev/empleados/operaciones/security/authentication/common; **`smu` sin ningún test**). ⚠️ **La suite global es imposible hoy**: `operaciones.0007` (`SeparateDatabaseAndState` + `RunSQL` con `ADD CONSTRAINT … FOREIGN KEY` y `DROP FOREIGN KEY`, sintaxis solo MySQL) revienta en SQLite (`OperationalError: near "CONSTRAINT"`) — cada app corre con su propio settings; fix propuesto: hacer el `RunSQL` condicional al `vendor`. ✅ `makemigrations --check` limpio en TODAS las apps y `manage.py check` ahora en **0 issues** (los 133 avisos drf-spectacular ya se corrigieron). Cobertura por app no medible globalmente por el crash; solo transporte tiene número confiable (93%). Lint global: ruff ~1.400 hallazgos (RUF012×193, I001×180, UP034×174, BLE001×152, **F401 imports sin usar ×131**, F841×17, F601 claves repetidas ×10 — revisar, pueden ser bugs reales), bandit 361 (todos LOW, mismas familias de falsos positivos), isort 312 archivos. Deuda global clasificada: tests de `smu`, fix del `RunSQL`, adopción de tooling (ruff/isort/black config) y revisión de F401/F601/S110 | `local` |
