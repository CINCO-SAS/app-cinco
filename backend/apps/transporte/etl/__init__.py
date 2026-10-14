"""
Paquete ETL del módulo transporte (F6 / §7 del plan).

Estructura preparada en el Tramo A (A3) y validada de verdad recién en C3
cuando exista conectividad con la BD legacy (gate G2):

- normalizadores: formatos legacy → contrato Django (D-A4, D-A6).
- convertidores: fila JSON → kwargs de modelo (puro, sin BD).
- carga: resolución de FKs, lotes de 2.000 y conciliación de conteos.

Comando: manage.py migrate_transporte_legacy (carpeta management/).
"""
