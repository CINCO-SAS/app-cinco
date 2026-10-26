# Plan Backend Django Consolidado — Módulo Transporte
## Adaptación estricta de la propuesta 2026 a la funcionalidad real verificada

**Fecha:** 13 de Octubre de 2026
**Versión:** 1.1 (Consolidada con reglas operativas elicitadas)
**Estado:** Especificación de backend derivada de [`PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md) (v2.0), corregida y completada contra el código fuente real de los 4 módulos PHP indicadores.
**Documentos con los que se consolida:** [`PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md), [`PLAN_MIGRACION.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_MIGRACION.md) (revisión 13-10), [`DICCIONARIO_DATOS.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/DICCIONARIO_DATOS.md), [`ANALISIS_TRANSPORTE_BASE_CONDUCTORES.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/ANALISIS_TRANSPORTE_BASE_CONDUCTORES.md).

> **Propósito de este documento:** el plan 2026 define la arquitectura de backend (5 modelos, 3 servicios). Este documento lo **adapta a la funcionalidad completa del módulo** (pestañas, herramientas y reglas verificadas línea por línea en los PHP), **corrige los errores que romperían el negocio o el ETL** y entrega el mapa funcionalidad → servicio → modelo → endpoint completo. Es la especificación que debe seguir el desarrollo en F1–F5.

---

## 1. Correcciones obligatorias al plan 2026 (antes de escribir una línea de código)

| # | Corrección | Evidencia en el código real | Decisión implementada en §3–§5 |
|---|---|---|---|
| **CR-1** | El `UniqueConstraint(vehiculo, fecha_salida)` **incondicional** rompe el flujo real: si una salida fue `ELIMINADO`, **sí se permite registrar otra el mismo día** | [`transporte_salida.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_salida.php) 447–458: `WHERE ... AND estado != 'ELIMINADO'` | Unique **parcial** con `condition=~Q(estado='ELIMINADO')` (§3.D) |
| **CR-2** | Mismo caso para móvil/conductor: la colisión real es contra salidas no eliminadas; legacy excluye sentinellas `'disponible'`/`'0'` | [`transporte_salida.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_salida.php) 482–496; [`base_salida_transporte.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_salida_transporte.php) 214 (`estado = 'APROBADO'` en consulta de UI) | Unique parcial `conductor NOT NULL AND estado != ELIMINADO` (§3.D) |
| **CR-3** | La BD actual **no tiene ningún UNIQUE**; placa con cardinalidad 1.258 en 1.246 filas (duplicados probables) y ~201k salidas sin restricción | [`DICCIONARIO_DATOS.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/DICCIONARIO_DATOS.md) §1, §2 | **Auditoría y deduplicación previa obligatoria** antes del ETL y antes de crear constraints (§7.1) |
| **CR-4** | El plan 2026 define 5 modelos; faltan ~9 (historial, novedades, bancarios, pagos, jefes, cierres, festivos, auditoría, documentos) | §4 vs §3 y diagrama ER | Modelos completados en §3 |
| **CR-5** | `Salida.area` NOT NULL + PROTECT fallaría en la carga histórica (área vive en el JSON `datos` y puede faltar) | [`DICCIONARIO_DATOS.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/DICCIONARIO_DATOS.md) §2 (columna `datos`) | `area = FK null=True`; la regla "área obligatoria si disponible" se valida en el servicio (§5.1) |
| **CR-6** | Adopción canónica de apps `common` y `empleados` de ADMCINCO; se descarta definitivamente la propuesta de `nucleo` | Consenso de arquitectura | **Decisión D-A2** (§2): reutilizar directamente `common.Area`, `common.Festivo`, `empleados.Empleado` |
| **CR-7** | El backend debe absorber **todas** las herramientas de las 3 pestañas + kiosco + flota + reporte fotográfico + planilla, no solo Tab 1 | Análisis funcional §1.5 de [`PLAN_MIGRACION.md`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/PLAN_MIGRACION.md) | Matriz completa en §6 |
| **CR-8** | Permisos por cédula hardcodeada en frontend (`1055837370` pestaña _fix, `1000756621` permi_especial, cédula de `permi_editar_fecha`) | [`base_salida_transporte.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_salida_transporte.php) 1652, 1695–1696 | Modelo `PermisoEspecial` / grupos Django (§5.9) |
| **CR-9** | La ventana de -2 días hábiles **sí aplica** en novedades y eliminación para el rol Operador Transporte (`esPerfilCarpetaTransporte`); solo Jefes y Admin tienen bypass | [`base_salida_transporte.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_salida_transporte.php) 760–770 (`id_row`), 877–889 (`del_base_salida`) | Validación contextual por rol en `SalidaService` (§5.1) |
| **CR-10** | Criterios de estado diferenciados: Pronto Pago suma **solo** `APROBADO`; Pago Mensual suma `APROBADO`, `REPORTADO` y `VALIDADO`; retrospectiva de 6 meses | [`base_salida_transporte.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_salida_transporte.php) 322–348, 395–400 | Métodos especializados en `LiquidacionService` (§5.2) |
| **CR-11** | Planillas y despachos se acotan a flota automotor por contrato (`PROPIO`, `EXTERNO`, `RENTING`) y **excluyen estrictamente motos** (`tipo != 'MOTO'`) | [`transporte_salida.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_salida.php) 640–682 (`generar_planilla_scope`) | Soporte de flota unificada y filtro duro en `PlanillaService` (§5.6) |
| **CR-12** | Nombres de esquemas/bases de datos quemados en SQL crudo (`bd_c3nc4s1s`, `cincosas_cincosas`) rompen la portabilidad | [`transporte_salida.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_salida.php) 730; [`base_transportadores.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_transportadores.php) 75 | Decisión **D-A10**: enrutamiento de base de datos (`DatabaseRouter`) en Django |
| **CR-13** | Importador CSV bancario exige auto-detección de delimitador (`;` o `,`), limpieza regex (`limpiarTexto`) y lógica de *upsert* por placa | [`base_transportadores.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_transportadores.php) 575–640 (`file_import_datos_bancarios`) | Contrato formal en `FlotaService.importar_datos_bancarios_csv` (§5.3) |

---

## 2. Decisiones técnicas cerradas (consolidadas)

| ID | Decisión | Valor | Fundamento |
|---|---|---|---|
| D-A1 | Motor destino | **MySQL 8 `utf8mb4_general_ci`** (coherencia con ADMCINCO y con el plan 2026). *Nota:* `PLAN_MIGRACION.md` proponía PostgreSQL; si el entorno lo permite, PostgreSQL es mejor opción — cerrar en F0 | Consistencia con ecosistema existente |
| D-A2 | Estructura de apps | Repositorio canónico [**`app-cinco`**](file:///c:/Users/admin/Documents/app-cinco): nueva app [`backend/apps/transporte/`](file:///c:/Users/admin/Documents/app-cinco/backend/apps/transporte/) + reutilizar directamente `common` (`Area`, `Festivo`, `Menu`, `AuditoriaModel`) y `empleados` (`Empleado`) | Integración limpia y directa con la arquitectura existente en `app-cinco` |
| D-A3 | Patrón por módulo | `models` → `services` (única capa de negocio) → `serializers` → `ViewSet` (contrato ADMCINCO) | Plan 2026 §5 |
| D-A4 | Zona horaria | `America/Bogota` con `USE_TZ=True`; fin del hack `-5 hour` ([`transporte_base_conductores.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_base_conductores.php) 13, etc.) | Verificado en los 4 archivos |
| D-A5 | Auditoría | `AuditableModel` base: `creado_por`, `creado_en`, `modificado_por`, `modificado_en` — reemplaza `edit`/`fecha_edit` en todas las tablas | Verificado en las 3 tablas |
| D-A6 | Estados | `TextChoices` en **mayúsculas** (`REPORTADO`, `APROBADO`, `RECHAZADO`, `ELIMINADO`, `VALIDADO`); la ETL normaliza el legacy que mezcla caja | [`base_salida_transporte.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/base_salida_transporte.php) 519 vs [`transporte_salida.php`](file:///c:/Users/admin/Documents/funcionalidades%20genericas/MIGRACIONES/transporte_salida.php) 214 |
| D-A7 | Corte | Construcción en paralelo + cutover único; rollback = puntero `config_menu.url` (<2 min); el PHP nunca se toca | Consenso de ambos planes |
| D-A8 | Fotos/QR | `media/transporte/...` con nombres normalizados; QR regenerado bajo demanda (no persistido) | Elimina `codigo_qr`/`codigo_barras` de BD |
| D-A9 | Base Negra Nokia | `asignar_movil` opera mediante evento asíncrono desacoplado (Background worker / Outbox); no bloquea despacho HTTP | Evita acoplamiento con base legacy |
| D-A10 | Desacoplamiento de BD | Enrutamiento limpio vía `settings.DATABASES` y `DatabaseRouter`. Prohibido el uso de prefijos SQL crudos (`bd_c3nc4s1s`, etc.) | CR-12: Mantenibilidad y seguridad |
| D-A11 | Máquina de Estados | Flujo formal en `Salida.estado`: `REPORTADO` → `APROBADO`/`RECHAZADO`/`ELIMINADO`; `APROBADO` → `VALIDADO`/`RECHAZADO`/`ELIMINADO`. Estados `RECHAZADO` y `ELIMINADO` son terminales | Previene transiciones inconsistentes |
| D-A12 | Unicidad en MySQL 8 | Implementación de Unique parcial en MySQL 8 mediante columna virtual calculada (`STORED`) que concatena IDs solo si `estado != 'ELIMINADO'` | Permite soporte nativo de CR-1 y CR-2 en MySQL 8 |
| D-A13 | Alcance de Flota (No Multi-Transporte) | **Exclusión absoluta de motos**. Módulo acotado a flota automotor de 4+ ruedas (`CAMIONETA`, `FURGÓN`, `VANS DE CARGA`, `VANS DE PASAJEROS`). Cero soporte multimodal | Regla de negocio: las motos no aplican ni forman parte de las operaciones de este subsistema |

---

## 3. Modelo de datos completo del backend ([`app-cinco/backend/apps/transporte/models/`](file:///c:/Users/admin/Documents/app-cinco/backend/apps/transporte/models/))

### 3.A Modelos base

```python
class AuditoriaModel(models.Model):          # D-A5
    creado_por = FK('empleados.Empleado', null=True)
    creado_en = DateTimeField(auto_now_add=True)
    modificado_por = FK('empleados.Empleado', null=True)
    modificado_en = DateTimeField(auto_now=True)
    class Meta: abstract = True

class Festivo(AuditableModel):               # alimenta ventana -2 días hábiles
    fecha = DateField(unique=True)
    descripcion = CharField(max_length=100)
    class Meta: db_table = 'transporte_festivo'
```

### 3.B Conductores y Flota

```python
class Conductor(AuditableModel):             # transporte_base_conductores (~108 filas)
    cedula = CharField(max_length=20, unique=True, db_index=True)   # auditar duplicados previos (CR-3)
    nombre_completo = CharField(max_length=150)
    celular = CharField(max_length=30)
    direccion = CharField(max_length=150, null=True, blank=True)
    barrio = CharField(max_length=100, null=True, blank=True)
    licencia_categoria = CharField(max_length=10, choices=CategoriaLicencia.choices, null=True)  # B1/C1/C2/C3
    licencia_vencimiento = DateField(null=True, blank=True)          # semáforo licencia también en servidor
    tipo_vinculacion = CharField(max_length=20, choices=Vinculacion.choices)  # EXTERNO/INTERNO (normalizar caja)
    fecha_ingreso = DateField()
    fecha_egreso = DateField(null=True, blank=True)                  # legacy: '0000-00-00' → NULL
    fecha_nacimiento = DateField(null=True, blank=True)              # edad DERIVADA, nunca persistida (corrige H2)
    activo = BooleanField(default=True, db_index=True)
    class Meta: db_table = 'transporte_conductor'
    # ELIMINADOS del legacy (verificados): placa (→ FK inverso), nombre/celular_propietario (→ Vehiculo),
    # tipo_vehiculo (duplica vehiculo.tipo), edad (derivada), estado texto, edit/fecha_edit (→ AuditoriaModel)

class Vehiculo(AuditableModel):              # transportadores_vehiculos (55 cols → modelo acotado)
    placa = CharField(max_length=10, unique=True, db_index=True)     # únicidad condicionada a auditoría CR-3
    tipo_vehiculo = CharField(max_length=50, choices=TipoVehiculo.choices)  # CAMIONETA/FURGON/VANS_CARGA/VANS_PASAJEROS (excluye MOTOS por D-A13)
    marca = CharField(max_length=50)
    referencia = CharField(max_length=50, null=True, blank=True)
    modelo_anio = PositiveSmallIntegerField()                        # era varchar
    color = CharField(max_length=40, null=True, blank=True)
    municipio_matricula = CharField(max_length=60, null=True, blank=True)
    numero_vin = CharField(max_length=50, null=True, blank=True)     # conservado (activo/inactivo)
    numero_motor = CharField(max_length=50, null=True, blank=True)   # conservado
    tipo_combustible = CharField(max_length=30, null=True, blank=True)
    kilometraje = IntegerField(null=True, blank=True)                # era texto
    cajon = BooleanField(default=False)                              # era 'SI'/'NO'
    logos = BooleanField(default=False)
    sistema_activo = TextField(null=True, blank=True)
    sistema_pasivo = TextField(null=True, blank=True)
    siniestros_viales = IntegerField(default=0)
    tipo_contrato = CharField(max_length=20, choices=Contrato.choices)   # PROPIO/EXTERNO/RENTING (elimina 'contrato' SI/NO)
    ciudad_operacion = CharField(max_length=30, null=True, choices=[...])  # MEDELLIN/MONTERIA/SINCELEJO
    conductor_habitual = FK(Conductor, on_delete=SET_NULL, null=True, related_name='vehiculos')
    nombre_propietario = CharField(max_length=150)                   # dueño vive SOLO aquí (verificado duplicado en conductores)
    cedula_propietario = CharField(max_length=20)
    celular_propietario = CharField(max_length=30, null=True, blank=True)
    fecha_ingreso = DateField(null=True, blank=True)
    fecha_egreso = DateField(null=True, blank=True)                  # '0000-00-00' → NULL
    fecha_soat = DateField(null=True, blank=True)
    fecha_cda = DateField(null=True, blank=True)
    valor_dia_base = DecimalField(max_digits=12, decimal_places=2, default=0)
    activo = BooleanField(default=True, db_index=True)
    # ELIMINADOS: nombre_conductor/cedual_conductor (→FK), tipo_conductor (→Conductor),
    # licencia/fecha_licencia/estado_licencia/categoria (pertenecen al conductor), como_cond (ambigua, auditar),
    # codigo_qr/codigo_barras (regenerables), 6 cols de mantenimiento (→ Mantenimiento 1:N),
    # edit/fecha_edit, estado texto
    class Meta: db_table = 'transporte_vehiculo'

class DocumentoVehiculo(AuditableModel):     # reemplaza img_soat/img_cda/img_matricula/img_carro
    TIPOS = Choices('SOAT','CDA','MATRICULA','FOTO_CARRO','TARJETA_OPERACION')
    vehiculo = FK(Vehiculo, related_name='documentos')
    tipo = CharField(max_length=30, choices=TIPOS)
    archivo = FileField(upload_to='transporte/vehiculos/%Y/')
    fecha_vencimiento = DateField(null=True, blank=True)             # SOAT/CDA alimentan el semáforo
    class Meta: db_table='transporte_documento_vehiculo'
        constraints=[UniqueConstraint(fields=['vehiculo','tipo'], name='uq_doc_vehiculo_tipo')]

class Mantenimiento(AuditableModel):         # legacy guardaba SOLO el último (historial perdido)
    vehiculo = FK(Vehiculo, related_name='mantenimientos')
    fecha = DateField()
    tipo = CharField(max_length=20, choices=[('CORRECTIVO',...),('PREVENTIVO',...),('NO_APLICA',...)])
    actividad_realizada = CharField(max_length=150)
    responsable = CharField(max_length=150)
    observacion = TextField(blank=True)
    proximo_mantenimiento = DateField(null=True)
    class Meta: db_table = 'transporte_mantenimiento'

class DatosBancariosVehiculo(AuditableModel):   # desempaquetado del JSON `datos.bancarios[]`
    vehiculo = FK(Vehiculo, related_name='datos_bancarios')
    cedula_titular = CharField(max_length=20)
    nombre_titular = CharField(max_length=150)
    banco = CharField(max_length=80)
    tipo_cuenta = CharField(max_length=30)
    numero_cuenta = CharField(max_length=30)
    activo = BooleanField(default=True)
    class Meta: db_table='transporte_datos_bancarios_vehiculo'
```

### 3.C Salidas (el corazón transaccional, ~201k filas)

```python
class Salida(AuditableModel):
    vehiculo = FK(Vehiculo, on_delete=PROTECT, related_name='salidas')
    fecha_salida = DateField(db_index=True)             # legacy datetime → día operativo (normalizar -5h en ETL)
    conductor = FK(Conductor, on_delete=PROTECT, null=True, blank=True, related_name='salidas')   # quien SALE (movil_sale)
    tecnico_asignado = FK(Empleado, on_delete=PROTECT, null=True, blank=True, related_name='salidas_como_movil')  # movil ASIGNADA (cedula_tecnico)
    es_disponible = BooleanField(default=False)         # reemplaza sentinellas 'disponible'/'0'
    area = FK('common.Area', on_delete=PROTECT, null=True, blank=True)   # CR-5: nullable solo por ETL histórico
    carpeta = CharField(max_length=100, null=True, blank=True)   # snapshot desde personal al momento de salir
    sede = CharField(max_length=100, null=True, blank=True)
    valor_dia = DecimalField(max_digits=12, decimal_places=2)    # SNAPSHOT inmutable de la tarifa
    estado = CharField(max_length=20, choices=EstadoSalida.choices, default=REPORTADO, db_index=True)
    observacion = TextField(blank=True)
    reportado = BooleanField(default=False)             # badge Reporte SI/NO (datos.reporte/reportes_adicionales)
    class Meta:
        db_table = 'transporte_salida'
        constraints = [
            # CR-1: colisiona SOLO contra salidas vivas (legacy: estado != 'ELIMINADO' en alta)
            models.UniqueConstraint(fields=['vehiculo','fecha_salida'],
                condition=~Q(estado='ELIMINADO'), name='uq_salida_vehiculo_fecha_viva'),
            # CR-2: mismo criterio para quien sale; 'disponible' ya no es fila (es NULL + flag)
            models.UniqueConstraint(fields=['conductor','fecha_salida'],
                condition=Q(conductor__isnull=False) & ~Q(estado='ELIMINADO'),
                name='uq_salida_conductor_fecha_viva'),
        ]
        indexes = [Index(fields=['fecha_salida','estado']), Index(fields=['area','fecha_salida'])]

class SalidaHistorial(AuditableModel):       # JSON longtext → 1:N consultable
    salida = FK(Salida, on_delete=CASCADE, related_name='historial')
    estado = CharField(max_length=20, choices=EstadoSalida.choices)
    motivo = TextField(blank=True)            # obligatorio en RECHAZADO (verificado: rechazar_salida exige motivo)
    fecha_cambio = DateTimeField()
    class Meta: db_table='transporte_salida_historial'

class Novedad(AuditableModel):               # datos.novedad → tabla; UNA por salida (legacy sobrescribe)
    salida = OneToOneField(Salida, on_delete=CASCADE, related_name='novedad')
    tipo = CharField(max_length=20, choices=[('ADICIONAL',...),('DESCUENTO',...)])
    valor = DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion = TextField()
    class Meta: db_table='transporte_novedad'
    # total a pagar = salida.valor_dia ± novedad.valor  → servicio calcular_pago() (§5.1)
```

### 3.D Liquidaciones, cierres y parámetros

```python
class FechaLimiteCierre(AuditableModel):     # transporte_registro_salida_fechas_limites
    mes = PositiveSmallIntegerField(); anio = PositiveIntegerField()
    fecha_limite = DateField()
    class Meta: db_table='transporte_fecha_limite_cierre'
        constraints=[UniqueConstraint(fields=['mes','anio'], name='uq_cierre_mes_anio')]  # reemplaza ON DUPLICATE KEY

class ConsecutivoMensual(AuditableModel):    # transporte_consecutivos_mensuales
    vehiculo = FK(Vehiculo, related_name='consecutivos')
    mes = PositiveSmallIntegerField(); anio = PositiveSmallIntegerField()
    consecutivo = PositiveIntegerField()
    class Meta: db_table='transporte_consecutivo_mensual'
        constraints=[UniqueConstraint(fields=['vehiculo','mes','anio'], name='uq_consecutivo_periodo')]

class PagoVehiculoMensual(AuditableModel):   # desempaquetado de datos.pago_mensual[] / pronto_pago[]
    vehiculo = FK(Vehiculo, related_name='pagos')
    mes = PositiveSmallIntegerField(); anio = PositiveSmallIntegerField()
    tipo = CharField(max_length=20, choices=[('MENSUAL',...),('PRONTO_PAGO',...)])
    pagado = BooleanField(default=False); fecha_pago = DateField(null=True)
    total_liquidado = DecimalField(max_digits=14, decimal_places=2, default=0)   # snapshot del cálculo
    class Meta: db_table='transporte_pago_vehiculo'
        constraints=[UniqueConstraint(fields=['vehiculo','mes','anio','tipo'], name='uq_pago_periodo_tipo')]

class JefeValidador(AuditableModel):         # programacion_parametros (JSON) → tabla consultable
    empleado = FK(Empleado, related_name='validaciones_transporte')
    areas = ManyToManyField(Area)
    carpetas_por_area = JSONField(default=dict)   # {"AREA": ["carpeta1",...]} (verificado en isUserLeaderOfSalida)
    activo = BooleanField(default=True)
    class Meta: db_table='transporte_jefe_validador'

class ValidacionSalida(AuditableModel):      # transporte_validacion_salidas (cierre mensual por área)
    area = FK(Area, related_name='validaciones_transporte')
    mes = PositiveSmallIntegerField(); anio = PositiveSmallIntegerField()
    datos = JSONField(default=dict)
    class Meta: db_table='transporte_validacion_salida'
        constraints=[UniqueConstraint(fields=['area','mes','anio'], name='uq_validacion_area_periodo')]

class ReporteFotograficoVehiculo(AuditableModel):   # alcance nuevo del plan 2026 (archivo NO verificado aún)
    vehiculo = FK(Vehiculo, related_name='reportes_fotos')
    responsable = FK(Empleado, related_name='reportes_fotos_creados')
    fecha = DateField(); hora = TimeField()
    ot_actividad = CharField(max_length=100, null=True, blank=True)
    imagen = ImageField(upload_to='transporte/reportes_diarios/%Y/%m/%d/')
    observaciones = TextField(blank=True)
    class Meta: db_table='transporte_reporte_fotografico'
        constraints=[UniqueConstraint(fields=['vehiculo','fecha'], name='uq_reporte_foto_vehiculo_dia')]

class AuditoriaLog(AuditableModel):          # transporte_log → genérico del módulo
    tabla = CharField(max_length=60); accion = CharField(max_length=20)
    registro_id = IntegerField(); datos_antes = JSONField(null=True); datos_despues = JSONField(null=True)
    class Meta: db_table='transporte_auditoria_log'
```

---

## 4. Modelo de dominio legacy → Django (mapeo ETL, resumen)

| Tabla legacy | Filas | Modelos destino | Transformaciones clave |
|---|---|---|---|
| `cinco_base_de_personal` | ~miles | `Empleado`/`Persona` (reutilizado) | cédula única; sede fuera del alcance |
| `transporte_base_conductores` | ~108 | `Conductor` | edad→derivada; placa/propietario/tipo_vehiculo→Vehiculo; `0000-00-00`→NULL; caja normalizada |
| `transportadores_vehiculos` | ~1.246 | `Vehiculo` + `DocumentoVehiculo` + `Mantenimiento` + `DatosBancariosVehiculo` | JSON `datos` desempaquetado; SI/NO→bool; números→int; 4 imgs→documentos; QR no persistido |
| `transporte_registro_salida` | ~200.811 | `Salida` + `SalidaHistorial` + `Novedad` | `historial` longtext→filas; `datos.novedad`→Novedad; sentinellas→flag; estados normalizados; cédulas resueltas a FK (conductor vs empleado) |
| `transporte_registro_salida_fechas_limites` | pequeño | `FechaLimiteCierre` | UNIQUE natural |
| `consecutivos_mensuales` | pequeño | `ConsecutivoMensual` | duplicados posibles → dedup previa |
| `transporte_validacion_salidas` | pequeño | `ValidacionSalida` | JSON `datos` se revisita en F0 |
| `programacion_parametros` (jefes) | pequeño | `JefeValidador` | JSON de áreas/carpetas → M2M + JSONField |
| `transporte_log` | acumula | `AuditoriaLog` | |
| Base negra `nokia_base_lineas` / `nokia_base_infraestructura` | externa | **Solo lectura** para cruces de teléfono; `asignar_movil` legacy ESCRIBE en ambas → **decisión pendiente D-A9** (§8) | |

---

## 5. Capa de servicios completa (`services.py`) — toda la regla verificada

### 5.1 `SalidaService` (Tab 1 Gestión + Tab Registro kiosco)

| Método | Reglas verificadas en el código (evidencia) |
|---|---|
| `ventana_validacion(fecha, usuario, accion)` | **Doble regla contextual (CR-9):**<br>1) Para **reportar**: fecha actual o máx. **2 días hábiles** atrás (festivos Colombia); bypass solo por permiso (`permi_programacion`/admin).<br>2) Para **novedades (`id_row`) y eliminación (`del_base_salida`)**: si el usuario es rol Operador Transporte (`esPerfilCarpetaTransporte`), la ventana de 2 días hábiles **sí aplica de forma estricta** (`base_salida_transporte.php` 760–770, 877–889). Solo los Jefes Validadores del área (`JefeValidador`) y administradores tienen bypass para gestionar registros fuera de ventana. |
| `registrar_salida(datos, actor)` | 1) Ventana -2 días hábiles; 2) Duplicado vehículo-día (`estado != ELIMINADO`) — **garantizado por constraint CR-1 y D-A12**; 3) **Exigencia estricta de personal:** Si NO es "disponible", exigir que quien sale tenga obligatoriamente **área y carpeta** en personal; si faltan, arrojar excepción bloqueante: *"La MOVIL {movil_sale} no tiene asignada un área o carpeta asignada, por favor verifique."* (`transporte_salida.php` 461–477). Si SÍ es "disponible", exigir selección manual de área en el formulario; 4) Snapshot `valor_dia`; 5) Historial inicial + `AuditoriaLog`; transacción atómica. |
| `aprobar_masivo(ids, actor)` | Transición permitida únicamente desde `REPORTADO` → `APROBADO` (D-A11). Actor debe ser jefe validador del **área de la salida** (`JefeValidador.areas/carpetas`) o tener permiso de programación; historial por fila; transacción atómica (`save_valid_transport`). |
| `rechazar(id, motivo, actor)` | **Motivo obligatorio** (legacy lo exige en modal); transición a estado `RECHAZADO`; `SalidaHistorial` almacena motivo y autor. Estado terminal inmutable. |
| `eliminar(id, actor)` | Borrado **lógico** (`ELIMINADO`) — nunca físico; requiere validación de ventana de 2 días para operadores de transporte (CR-9); libera la restricción única del vehículo para permitir otro despacho el mismo día (CR-1). |
| `registrar_novedad(salida_id, tipo, valor, descripcion, actor)` | Una por salida (sobrescribe como legacy); `tipo ∈ {ADICIONAL, DESCUENTO}`; cálculo total en servidor: `valor_dia + valor` (adicional) / `valor_dia - valor` (descuento); validación de ventana según rol (CR-9). |
| `eliminar_novedad(salida_id, actor)` | Limpia la novedad con auditoría (legacy: `rep_novedad` vacío o null en `id_row`, limpiando `tipo`, `valor`, `descripcion`). |
| `calcular_pago(salida)` | `valor_dia ± novedad` — una sola implementación determinista en backend. |
| `buscar_movil(cedula)` | Búsqueda en cascada: (1) Conductor externo (`transporte_base_conductores`) → (2) Personal (`cinco_base_de_personal`) → (3) Línea corporativa Nokia (`nokia_base_lineas` vía router D-A10). |

### 5.2 `LiquidacionService` (Tab 3 Liquidaciones)

- **`sabana_pago_mensual(mes, anio, filtros)` (CR-10):** Agrupa salidas por vehículo del mes consultado considerando **únicamente** los estados `APROBADO`, `REPORTADO` y `VALIDADO` (`base_salida_transporte.php` 395–400). Fórmula: `Σ(días trabajados × valor_dia) ± novedades`.
- **`sabana_pronto_pago(mes, anio, filtros)` (CR-10):** Modalidad anticipada. Agrupa salidas considerando **exclusivamente** salidas con estado `APROBADO` (`base_salida_transporte.php` 322).
- **Búsqueda retrospectiva histórica (CR-10):** Si para el mes y año consultado no existen registros de pronto pago parametrizados, el servicio ejecuta un bucle retrospectivo de hasta **6 meses atrás** (`for ($i = 1; $i <= 6; $i++)`) buscando la última vigencia registrada.
- **`obtener_o_generar_consecutivo(vehiculo, mes, anio)`:** **`select_for_update()`** sobre `ConsecutivoMensual` — erradica la condición de carrera `MAX+1` detectada en `base_salida_transporte.php` 234–286.
- **`cerrar_mes(mes, anio, fecha_limite, actor)`:** Gestiona `FechaLimiteCierre` (permiso `editar_tras_cierre`).

### 5.3 `FlotaService` (ABM vehículos — Tab Base Transportadores)

- CRUD vehículo con validación de **placa única** (tras auditoría CR-3), semáforo SOAT/CDA **en servidor** (`>60` verde, `31–60` naranja, `≤30` rojo — regla verificada `base_salida_transporte.php` 2022–2024), subida de documentos con validación tipo/tamaño, QR regenerado bajo demanda.
- **`importar_datos_bancarios_csv(archivo)` (CR-13):**
  1. Auto-detección del separador de columnas (`;` vs `,`).
  2. Sanitización alfanumérica estricta de textos y cuentas (`limpiarTexto` regex `[^a-zA-Z0-9\s]`).
  3. Lógica **Upsert**: si el vehículo ya tiene cuenta registrada, actualiza banco/cuenta/titular; si no existe, la crea. Reporta filas rechazadas con causas explícitas.

### 5.4 `ConductorService` (catálogo conductores)

- CRUD con unicidad de cédula (auditar duplicados previos), edad derivada de `fecha_nacimiento` (nunca persistida en BD; corrige `transporte_base_conductores.php` 454–458), validación de vencimiento de licencia (semáforo), `fecha_egreso` solo al poner `INACTIVO`.

### 5.5 `ReporteFotograficoService` (alcance nuevo, pendiente de verificación de origen)

- `validar_agenda_responsable(empleado_id, fecha)`: responsable con agenda hoy en `operaciones_agenda` (salvo exentos).
- `validar_horario_captura(hora)`: solo **10:00–16:00** (Bogotá).
- `guardar_evidencia(...)`: compresión `Pillow` (~500–800 KB) + metadatos de auditoría.
- **Nota:** reglas provenientes de `transporte_reporte_vehiculo_inc.php`, archivo aún no verificado (§8).

### 5.6 `PlanillaService` (CR-11)

- **`generar_planilla(fecha, alcance, placas)`:**
  1. **Alcance individual (`PLACA`):** genera despacho con consecutivo correlativo mensual para el vehículo solicitado.
  2. **Alcance por lote (`PROPIO`, `EXTERNO`, `RENTING`):** genera despacho masivo de todos los vehículos activos bajo esa modalidad contractual (`transporte_salida.php` 640–682).
  3. **Filtro excluyente duro:** **exclusión obligatoria de motocicletas (`tipo != 'MOTO'`)** de cualquier formato de planilla oficial.
  4. Código QR dinámico de verificación impreso en el formato.

### 5.7 `InformeService` (Tab 2 Informes)

- Consulta mensual de salidas no eliminadas (reemplaza `consulta`), filtros multidimensionales (fecha, estado, sede, área), exportación Excel/CSV (hoy client-side con DataTables → **server-side**).

### 5.8 `ParametrosService`

- Jefes validadores (reemplaza `upload_jefes_valid`/`get_valid_trans`), áreas/carpetas (reemplaza `loadMapAreasCarpetas` y `infraestructura_parametros`), fechas límite (reemplaza `get_all_fecha`/`guardar_permi_editar_fecha`).

### 5.9 `PermisoService` (elimina las cédulas hardcodeadas)

| Cédula / marca actual | Permiso Django propuesto |
|---|---|
| cédulas admin hardcodeadas (PHP) | grupo `transporte_admin` |
| `$permi_programacion` | permiso `transporte.puede_programar` |
| jefes por área (`programacion_parametros`) | modelo `JefeValidador` |
| `permi_especial` (1000756621) | permiso `transporte.permiso_especial` |
| `permi_editar_fecha` (cédula oculta) | permiso `transporte.editar_tras_cierre` |
| pestaña Datos `_fix` (1055837370) | eliminar la bifurcación; permisos por funcionalidad |
| perfil carpeta TRANSPORTE (`esPerfilCarpetaTransporte`) | grupo `transporte_operador` |

---

## 6. Matriz funcionalidad → servicio → modelo → endpoint (control "nada se pierde")

> Cada fila debe quedar `VERIFICADA` con pruebas antes del cutover. IDs según el inventario funcional de `PLAN_MIGRACION.md` §1.5–§1.6.

| ID | Funcionalidad (herramienta real) | Endpoint Django | Servicio | Modelo |
|---|---|---|---|---|
| B1 | Filtro rango de fechas con rangos rápidos | `GET /salidas/?desde=&hasta=` (server-side) | `SalidaService.listar` | Salida |
| B2 | Visualizar fechas de cierre | `GET /cierres/` | `ParametrosService` | FechaLimiteCierre |
| B3 | Leer/asignar fecha límite de edición | `GET/PATCH /cierres/{mes}/{anio}/` | `LiquidacionService.cerrar_mes` | FechaLimiteCierre |
| B4 | DataTable + exportar Excel | `GET /salidas/export/?format=xlsx` | `InformeService` | Salida |
| B5 | Eliminar reporte (lógico) con validación de ventana para rol Transporte | `DELETE /salidas/{id}/` | `SalidaService.eliminar` | Salida + Historial |
| B6 | Reportar novedad (con total en vivo y ventana según rol) | `POST /salidas/{id}/novedad/` | `SalidaService.registrar_novedad` | Novedad |
| B7 | Eliminar novedad (limpia tipo/valor/desc con auditoría) | `DELETE /salidas/{id}/novedad/` | `SalidaService.eliminar_novedad` | Novedad |
| B8 | Ficha vehículo + semáforo SOAT/CDA | `GET /vehiculos/{id}/resumen/` | `FlotaService` | Vehiculo, DocumentoVehiculo |
| B9 | Ficha móvil asignada / móvil sale (técnico + auxiliar) | `GET /personas/{cedula}/ficha-movil/` | `SalidaService.buscar_movil` | Empleado |
| B10 | Columnas valor día / valor novedad / total | incluido en `GET /salidas/` | `SalidaService.calcular_pago` | Salida, Novedad |
| B11 | Área–carpeta con centro de costos | incluido en listados | `ParametrosService` | Area |
| B12 | **Validación masiva** de salidas | `POST /salidas/aprobar-lote/` | `SalidaService.aprobar_masivo` | Salida + Historial |
| B13 | Rechazo individual con motivo obligatorio | `POST /salidas/{id}/rechazar/` | `SalidaService.rechazar` | Salida + Historial |
| B14 | Badge Reporte SI/NO | campo `reportado` en `GET /salidas/` | — | Salida |
| B15 | Permisos por fila (jefe área/carpeta, ventana) | evaluados en serializer | `PermisoService` | JefeValidador |
| I1 | Tab 2: informes/sábana con filtros | `GET /informes/mensual/` | `InformeService` | Salida |
| D1 | Tab 3: jefes validadores | `CRUD /parametros/jefes/` | `ParametrosService` | JefeValidador |
| D2 | Tab 3: fechas límite | `CRUD /parametros/cierres/` | `LiquidacionService` | FechaLimiteCierre |
| D3 | Tab 3: liquidaciones + consecutivos atómicos | `GET /liquidaciones/{anio}/{mes}/`, `POST .../consecutivo/` | `LiquidacionService` | ConsecutivoMensual, PagoVehiculoMensual |
| D4 | Tab 3: pago mensual (aprob/rep/val) / pronto pago (aprob) | `GET /liquidaciones/pago-mensual/`, `/pronto-pago/` | `LiquidacionService` | PagoVehiculoMensual |
| S1 | Kiosco: escáner QR / cámara | `POST /kiosco/escanear/` (device camera) | `FlotaService` | Vehiculo |
| S2 | Asignar móvil (evento asíncrono outbox hacia Nokia) | `POST /kiosco/asignar-movil/` | `SalidaService` | Empleado (+decisión D-A9) |
| S3 | Validar fecha/vehículo/móvil | `POST /kiosco/validar/` | `SalidaService` | Salida |
| S4 | Consulta por placa + estado del día | `GET /kiosco/vehiculo/{placa}/` | `FlotaService` | Vehiculo, Salida |
| S5 | Planilla de salida (alcance PLACA o contrato PROPIO/EXTERNO/RENTING; exclusión MOTOS) | `POST/GET /planillas/?alcance=&fecha=` | `PlanillaService` | Salida, ConsecutivoMensual |
| S6 | Grabar salida (exige área/carpeta si no disponible) | `POST /salidas/` | `SalidaService.registrar_salida` | Salida |
| T1–T6 | Flota: ficha, fotos/docs, bancarios, import CSV (upsert), QR, teléfonos | `CRUD /vehiculos/`, `POST .../documentos/`, `POST .../importar-bancarios/`, `GET .../qr.png` | `FlotaService` | Vehiculo + auxiliares |
| C1 | Conductores ABM | `CRUD /conductores/` | `ConductorService` | Conductor |
| F1 | Reporte fotográfico diario (10a–4p + agenda) | `POST /reportes-fotograficos/` | `ReporteFotograficoService` | ReporteFotograficoVehiculo |
| E1 | Reemplazo del controlador externo `get_vehiculos_transp` | `GET /vehiculos/catalogo-operativo/` | `FlotaService` | Vehiculo |
| E2 | Reemplazo de helpers JS globales (búsquedas, alertas) | endpoints `?q=&limit=` + mensajes de error estandarizados | varios | — |
| E3 | Reemplazo de cédulas hardcodeadas por permisos | `GET /permisos/estado/` | `PermisoService` | JefeValidador/grupos |

---

## 7. Estrategia de ETL y cutover (corregida)

### 7.1 Auditoría previa obligatoria (solo lectura, bloquea F6 si falla)
1. Duplicados de **placa** (índice actual cardinalidad 1.258 > 1.246 filas) → decide si `placa unique` es posible.
2. Duplicados de **cédula** en conductores (~108 filas).
3. Salidas (vehículo, día) y (móvil, día) repetidas **con estados vivos distintos de ELIMINADO** → definen si los constraints CR-1/CR-2 sobreviven; si no, UNIQUE solo donde los datos lo permitan y el resto se refuerza en el servicio con advisory lock.
4. Fechas cero (`0000-00-00`), JSON inválido en `datos`/`historial`, estados fuera de catálogo, cédulas huérfanas.

### 7.2 Convertidores JSON (con reporte de filas no convertibles)
- `historial` longtext → filas `SalidaHistorial` (estado, edit, fecha_edit, fecha_salida).
- `datos.novedad` → `Novedad` (tipo/valor/descripcion/autor/fecha).
- `datos` bancarios[] → `DatosBancariosVehiculo`; `pago_mensual[]`/`pronto_pago[]` → `PagoVehiculoMensual`.
- `datos.area_sale/carpeta_sale/sede_sale` → FK/snapshots; `datos.placa` descartado (FK); `datos.valor_dia` → campo `valor_dia` de `Salida`.
- `programacion_parametros.datos` (jefes) → `JefeValidador` (áreas M2M + carpetas JSON).

### 7.3 Carga y verificación
- `manage.py migrate_transporte_legacy` por lotes (2.000 filas/batch), resolución de FKs por cédula (conductor externo vs empleado), normalización de estados a mayúsculas, `-5h` → `America/Bogota`.
- Reconciliador: conteos por tabla, muestras cruzadas, totales de liquidación del mes actual PHP vs Django (**discrepancia $0**).
- Cutover: congelación breve → carga final → puntero `config_menu.url` → validación; rollback = devolver puntero (<2 min).

---

## 8. Pendientes explícitos que bloquean el arranque de F3+

| # | Pendiente | A quién | Bloquea |
|---|---|---|---|
| P1 | Archivos no verificados: `transporte_reporte_vehiculo_inc.php`, `planilla_salida.php`, `transporte_salida_informes.php`, `transporte_salida_datos(_fix).php`, `controller_cinco.php`, `gerencia_informes_vehiculos_controlador.php` | Dueño del sistema | F3, F5, cierre de §5.5/§5.6/§5.7 |
| P2 | Decisión D-A1 (motor MySQL vs PostgreSQL) y D-A9 (fuente de verdad base negra) | Equipo / Negocio | F1 |
| P3 | **D-A9:** `asignar_movil` legacy escribe en `cinco_base_de_personal.placa` **y** `nokia_base_infraestructura.placa` (base negra). ¿Fuente de verdad? ¿Sigue escribiendo en ambas? | Dueño de negocio | S2 |
| P4 | Confirmar: ventana de novedades después del cierre mensual; `fecha_egreso` obligatoria al inactivar conductor | Dueño de negocio | §5.1, §5.4 |
| P5 | Resultado de la auditoría de duplicados (§7.1) para confirmar constraints | Datos | F6 |

---

*Documento de especificación backend. Ningún archivo del sistema actual fue modificado. Debe leerse junto con `PLAN_TECNICO_MIGRACION_MODULO_TRANSPORTE_2026.md` (arquitectura y cronograma) y `PLAN_MIGRACION.md` §1.5 (inventario funcional detallado).*
