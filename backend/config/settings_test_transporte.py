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

import tempfile

# Aíslamos MEDIA_ROOT: sin esto, cada test que crea un vehículo escribiría
# su PNG en la carpeta real backend/media/transporte/codigos-qr/, que es
# la que usa el negocio (contaminación de datos reales en cada corrida).
MEDIA_ROOT = tempfile.mkdtemp(prefix="transporte_test_media_root_")

MIGRATION_MODULES = {
    "authentication": None,
    "common": None,
    "security": None,
    "operaciones": None,
    "empleados": None,
    "ia_dev": None,
    "transporte": None,
}
