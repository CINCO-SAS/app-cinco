# Diccionario de datos — Módulo Transporte (sistema "Cinco")

Base de datos: `bd_c3nc4s1s` (servidor 192.168.79.10)
Cotejamiento por defecto de tablas: `utf8mb4_0900_ai_ci` (MySQL 8)

---

## 1. `transportadores_vehiculos` — Flota / vehículos

- **Registros:** ~1.246 (auto-increment sigue en 2.127 → hubo borrados)
- **Tamaño:** 2.5 MB datos + 320 KB índices
- **Creada:** 2024-08-05
- **Columnas:** 55
- **Relaciones/FK:** ninguna

### Columnas

| # | Columna | Tipo | Nulo | Defecto | Observación |
|---|---------|------|------|---------|-------------|
| 1 | `id` | int AI | No | - | PK |
| 2 | `tipo` | varchar(55) latin1 | No | - | CAMIONETA, FURGON, MOTO... |
| 3 | `marca` | varchar(55) latin1 | No | - | |
| 4 | `referencia` | varchar(55) latin1 | No | - | |
| 5 | `modelo` | varchar(11) latin1 | No | - | año, como texto |
| 6 | `cilindraje` | varchar(11) latin1 | No | - | numérico como texto |
| 7 | `color` | varchar(55) latin1 | No | - | |
| 8 | `placa` | varchar(11) latin1 | No | - | **NO única** (solo índice) |
| 9 | `municipio_matricula` | varchar(55) latin1 | No | - | |
| 10 | `numero_vin` | varchar(50) latin1 | No | - | |
| 11 | `tipo_contrato` | varchar(20) | No | EXTERNO | PROPIO / EXTERNO / RENTING |
| 12 | `tipo_conductor` | varchar(20) | **Sí** | NULL | |
| 13 | `cajon` | varchar(11) | No | - | SI/NO |
| 14 | `logos` | varchar(11) | No | - | SI/NO |
| 15 | `como_cond` | varchar(11) | No | - | SI/NO |
| 16 | `propietario` | varchar(255) utf8mb3 | No | - | |
| 17 | `cedula` | varchar(20) | No | - | cédula del PROPIETARIO |
| 18 | `fecha_ingreso` | datetime | No | - | |
| 19 | `fecha_egreso` | datetime | No | - | JS lee '0000-00-00 00:00:00' |
| 20 | `img_soat` | text | No | - | ruta relativa |
| 21 | `fecha_soat` | datetime | No | - | vencimiento SOAT |
| 22 | `img_cda` | text | No | - | ruta relativa |
| 23 | `fecha_cda` | datetime | No | - | vencimiento CDA |
| 24 | `img_matricula` | text | No | - | ruta relativa |
| 25 | `estado` | varchar(55) | No | - | ACTIVO / INACTIVO (índice, 2 valores) |
| 26 | `cedual_conductor` | varchar(55) | No | - | **typo en BD**: "cedual" |
| 27 | `edit` | text | No | - | guarda cédula (texto) |
| 28 | `fecha_edit` | datetime | No | - | |
| 29 | `img_carro` | text | No | - | ruta relativa |
| 30 | `numero_motor` | varchar(255) | No | - | |
| 31 | `tipo_combustible` | varchar(100) | No | - | |
| 32 | `sistema_activo` | text | No | - | seguridad activa |
| 33 | `sistema_pasivo` | text | No | - | seguridad pasiva |
| 34 | `kilometraje` | varchar(11) | No | - | numérico como texto |
| 35 | `licencia` | varchar(50) | No | - | SI/NO/NO APLICA |
| 36 | `fecha_licencia` | datetime | No | - | |
| 37 | `estado_licencia` | varchar(50) | No | - | ACTIVA/INACTIVA |
| 38 | `categoria` | varchar(50) | No | - | A1..C3 |
| 39 | `tarjeta` | varchar(50) | No | - | SI/NO/NO APLICA |
| 40 | `fecha_tarjeta` | datetime | No | - | |
| 41 | `contrato` | varchar(5) | No | - | SI/NO |
| 42 | `ultima_revicion` | datetime | No | - | **typo**: "revicion" |
| 43 | `tipo_mantenimiento` | varchar(15) | No | - | CORRECTIVO/PREVENTIDO/NO APLICA |
| 44 | `actividad_realizada` | varchar(150) | No | - | |
| 45 | `responsable` | varchar(150) | No | - | |
| 46 | `proximo_mantenimiento` | datetime | No | - | |
| 47 | `observacion_revicion` | text | No | - | **typo**: "revicion" |
| 48 | `nombre_conductor` | varchar(255) | No | - | desnormalizado |
| 49 | `movil_asignada` | varchar(15) utf8mb3 | **Sí** | NULL | cédula del técnico |
| 50 | `ciudad_operacion` | varchar(30) utf8mb3 | **Sí** | NULL | MEDELLIN/MONTERIA/SINCELEJO |
| 51 | `codigo_qr` | text | No | - | ruta PNG del QR |
| 52 | `codigo_barras` | text | No | - | |
| 53 | `valor_dia` | int | No | 0 | COP por día |
| 54 | `siniestros_viales` | int | No | - | sin defecto explícito |
| 55 | `datos` | json | **Sí** | NULL | datos_bancarios[], pago_mensual[], pronto_pago[] |

### Índices

| Nombre | Columna | Único | Cardinalidad |
|--------|---------|-------|--------------|
| PRIMARY | id | Sí | 1.246 |
| (idx) | modelo | No | 27 |
| (idx) | placa | No | 1.258 |
| (idx) | cedula | No | 1.104 |
| (idx) | propietario | No | 1.134 |
| (idx) | estado | No | 2 |
| (idx) | cedual_conductor | No | 1.110 |

### Hallazgos clave

1. **`placa` NO es UNIQUE** → la validación "placa duplicada" solo existe en PHP.
2. **Cotejamientos mixtos**: tabla utf8mb4, pero ~35 columnas en `latin1_swedish_ci` y 3 en `utf8mb3_general_ci`.
3. **Sin foreign keys**: `movil_asignada` y `cedual_conductor` apuntan a `cinco_base_de_personal.cedula` sin integridad referencial.
4. Muchas columnas NOT NULL sin defecto → inserts deben enviarlas siempre (o guardar cadenas vacías).
5. Fechas "sentinella": el JS del sistema compara contra `'0000-00-00 00:00:00'` (posibles ceros en datos históricos).
6. `datos` (JSON) concentra: datos bancarios (array), marcas de pago mensual y pronto pago → en Django: `JSONField` o modelos propios.
7. `edit` es TEXT pero guarda una cédula → candidato a ForeignKey en la migración.
8. Typos que conviene **no** propagar al esquema nuevo: `cedual_conductor`, `ultima_revicion`, `observacion_revicion`.

---

## 2. `transporte_registro_salida` — Registros de salidas de vehículos

- **Registros:** ~200.811 (la tabla transaccional grande del módulo)
- **Cotejamiento por defecto:** `utf8mb4_unicode_ci` (distinto al de la tabla 1 → tablas creadas en épocas distintas)
- **Columnas:** 11
- **Relaciones/FK:** ninguna

### Columnas

| # | Columna | Tipo | Nulo | Defecto | Observación |
|---|---------|------|------|---------|-------------|
| 1 | `id` | int AI | No | - | PK |
| 2 | `fecha_salida` | datetime | No | - | fecha/hora de salida |
| 3 | `id_vehiculo` | int | No | - | referencia lógica a `transportadores_vehiculos.id` (sin FK) |
| 4 | `cedula_tecnico` | **int** | No | - | cédula del móvil ASIGNADA al vehículo; **int aquí, varchar en la tabla 1** |
| 5 | `movil_sale` | varchar(50) | No | - | cédula de quien SALE; admite sentinellas 'disponible' y '0' |
| 6 | `observacion` | text | No | - | |
| 7 | `estado` | varchar(20) | No | **'reportado'** | reportado/aprobado/rechazado/eliminado/validado |
| 8 | `historial` | **longtext** | No | - | JSON como texto (array de cambios de estado) |
| 9 | `datos` | **json** | No | - | placa, valor_dia, area_sale, carpeta_sale, sede_sale, novedad{...} |
| 10 | `edit` | varchar(20) | **Sí** | NULL | cédula del último editor |
| 11 | `fecha_edit` | timestamp | No | CURRENT_TIMESTAMP | |

### Índices

| Nombre | Columna | Único | Cardinalidad |
|--------|---------|-------|--------------|
| PRIMARY | id | Sí | 200.811 |
| (idx) | fecha_salida | No | 71.510 |
| (idx) | cedula_tecnico | No | 1.201 |
| (idx) | movil_sale | No | 1.242 |

### Hallazgos clave

1. **Sin UNIQUE sobre (id_vehiculo, fecha)** → la regla "un vehículo no sale dos veces el mismo día" solo vive en el PHP; los ~200k registros históricos podrían contener duplicados que validar antes de imponer restricción en Django.
2. **`historial` es longtext vs `datos` es json** → inconsistencia de tipos; en Django ambos serían JSONField (o `historial` en modelo aparte `HistorialSalida`).
3. **Tipos heterogéneos de cédula**: `cedula_tecnico` int, `movil_sale` varchar(50), `edit` varchar(20) — mismo concepto de dominio con 3 tipos distintos → unificar (varchar o FK a Persona) en la migración.
4. `movil_sale` almacena valores no-persona ('disponible', '0') → en Django mejor modelar con un flag `disponible` booleano + FK nullable.
5. `estado` con defecto 'reportado' → coincide con el flujo del PHP (reportado → aprobado/rechazado/eliminado/validado). Ojo: el PHP usa mayúsculas en algunas queries ('APROBADO') y minúsculas en otras; MySQL lo tolera por collation, Django/ORM no.
6. **Volumen ~200k filas**: la carga de datos iniciales debe ser por lotes (bulk), no fila a fila.
7. `fecha_edit` timestamp automático (DEFAULT CURRENT_TIMESTAMP) vs `edit` nullable → auditoría a medias.

---

## 3. `transporte_base_conductores` — Base de conductores

- **Registros:** ~108 (tabla pequeña)
- **Cotejamiento por defecto:** `utf8mb3_unicode_ci` (3 bytes, legado)
- **Creada:** 2023-12-15
- **Columnas:** 20
- **Índices:** solo PRIMARY (id) — **`cedula` y `placa` sin índice**

### Columnas

| # | Columna | Tipo | Nulo | Defecto | Observación |
|---|---------|------|------|---------|-------------|
| 1 | `id` | int AI | No | - | PK |
| 2 | `cedula` | varchar(20) utf8mb3 | No | - | **sin índice** |
| 3 | `nombre_conductor` | varchar(100) | No | - | |
| 4 | `nombre_propietario` | varchar(100) | No | - | |
| 5 | `edad` | varchar(11) | No | - | **edad guardada como texto** (dato derivado/desactualizable) |
| 6 | `tipo_vinculacion` | varchar(50) | No | - | externo/interno |
| 7 | `celular_conductor` | varchar(20) | No | - | |
| 8 | `celular_propietario` | varchar(20) | No | - | |
| 9 | `direccion` | varchar(100) | No | - | |
| 10 | `barrio` | varchar(100) | No | - | |
| 11 | `tipo_vehiculo` | varchar(20) | No | - | CAMIONETA/FURGÓN/VANS... |
| 12 | `placa` | varchar(10) | No | - | **sin índice**; 1 placa por conductor (desnormalizado) |
| 13 | `licencia` | varchar(100) | No | - | categoría B1/C1/C2/C3 |
| 14 | `fecha_vencimiento_licencia` | timestamp | No | - | |
| 15 | `fecha_ingreso` | timestamp | No | - | |
| 16 | `fecha_egreso` | timestamp | No | - | el PHP INSERTA sin esta columna → posible '0000-00-00' |
| 17 | `fecha_nacimiento` | timestamp | No | - | |
| 18 | `estado` | varchar(20) | No | - | ACTIVO/INACTIVO |
| 19 | `edit` | varchar(20) | No | - | cédula del editor |
| 20 | `fecha_edit` | timestamp | No | CURRENT_TIMESTAMP | **ON UPDATE CURRENT_TIMESTAMP** (única tabla con auto-update) |

### Hallazgos clave

1. **Tabla diminuta (~108 filas)** → migración trivial.
2. **Sin índice en `cedula`** aunque el PHP consulta `WHERE cedula = ?` (get_telefonos_conductores) → full scan actual; en Django conviene `db_index` o unique.
3. **`edad` como varchar** → derivada de `fecha_nacimiento`; en Django calcularla, no guardarla.
4. **Posibles fechas cero**: el INSERT de `transporte_base_conductores.php` no envía `fecha_egreso` en altas, pero la columna es NOT NULL sin defecto → en modo no-strict MySQL guardó '0000-00-00 00:00:00' (el JS del sistema lo comprueba explícitamente). Detectar y convertir a NULL/empty en la migración.
5. **Redundancia entre las 3 tablas**: nombre/conductor y placa viven aquí y también en `transportadores_vehiculos` (nombre_conductor, cedual_conductor). En Django: modelo Conductor + FK desde Vehículo, sin duplicar.
6. utf8mb3 → pasar a utf8mb4.
7. Es la única con `ON UPDATE CURRENT_TIMESTAMP` en fecha_edit.
