"""
Settings exclusivos para los tests del módulo Transporte.

Hereda de settings_test (SQLite en memoria, sin MySQL) y desactiva las
migraciones de las apps locales: el esquema de test se crea directamente
desde los modelos. Así los tests de transporte no dependen de migraciones
de otros módulos (aislamiento: transporte se prueba solo).

Uso:
    python backend/manage.py test apps.transporte --settings=config.settings_test_transporte
"""
from .settings_test import *  # noqa: F401,F403

MIGRATION_MODULES = {
    "authentication": None,
    "common": None,
    "security": None,
    "operaciones": None,
    "empleados": None,
    "ia_dev": None,
    "transporte": None,
}
