"""Pruebas unitarias para la sincronización de usuarios en auth_user.

Ejecutar con: python -m unittest discover -s scripts/tests -v (desde backend).
"""
import csv
import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
        SECRET_KEY="synthetic-test-key",
    )
django.setup()

# Salvaguarda de seguridad: garantizar que solo opere en SQLite en memoria
_db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
_db_name = settings.DATABASES.get("default", {}).get("NAME", "")
if "sqlite3" not in _db_engine or _db_name != ":memory:":
    raise RuntimeError(
        "Esta suite de pruebas requiere una base de datos SQLite en memoria ':memory:' "
        "para prevenir modificaciones accidentales sobre bases de datos reales o de desarrollo."
    )

from django.contrib.auth.models import User
from django.db import IntegrityError, connection, transaction
from scripts import sync_auth_users as sync


class SyncAuthUsersTests(unittest.TestCase):
    """Conjunto de pruebas para validar la sincronización y manejo de unicidad en sync_auth_users."""

    @classmethod
    def setUpClass(cls):
        """Crea el esquema temporal en memoria para el modelo User."""
        with connection.schema_editor() as editor:
            editor.create_model(User)

    @classmethod
    def tearDownClass(cls):
        """Elimina el esquema temporal en memoria."""
        with connection.schema_editor() as editor:
            editor.delete_model(User)

    def setUp(self):
        """Limpia la tabla auth_user en memoria antes de cada prueba."""
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_user")

    def run_import(self, rows, *options, total_count=2):
        """Ejecuta el script de importación con salida redirigida y argumentos simulados."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "users.csv"
            stdout = io.StringIO()
            with (
                patch("sys.argv", ["sync_auth_users", "--output", str(output), *options]),
                patch.object(sync, "setup_django"),
                patch.object(sync, "get_total_rows", return_value=total_count),
                patch.object(sync, "fetch_source_rows", side_effect=lambda _: rows()),
                redirect_stdout(stdout),
            ):
                self.assertEqual(sync.main(), 0)
            with output.open() as exported:
                return stdout.getvalue(), list(csv.reader(exported))

    def test_concurrent_id_and_username_conflicts_continue(self):
        """Verifica que conflictos concurrentes de ID o username se salten sin abortar."""
        for conflict in ("id", "username"):
            with self.subTest(conflict=conflict):
                self.setUp()

                def rows():
                    User.objects.create(
                        id=1 if conflict == "id" else 99,
                        username="taken" if conflict == "username" else "other",
                    )
                    yield (1, "taken", "", "", "", "ACTIVO")
                    yield (2, "fresh", "", "", "", "ACTIVO")

                with transaction.atomic():
                    stdout, exported = self.run_import(rows)
                    self.assertTrue(User.objects.filter(id=2, username="fresh").exists())
                self.assertIn("Creados: 1. Actualizados: 0. Saltados: 1.", stdout)
                self.assertEqual([row[0] for row in exported], ["username", "fresh"])

    def test_other_integrity_error_propagates(self):
        """Verifica que errores de integridad ajenos a colisión de identidad se propaguen."""
        error = IntegrityError("not null")
        error.__cause__ = sqlite3.IntegrityError("NOT NULL constraint failed: auth_user.email")

        with patch.object(User, "save", side_effect=error):
            with self.assertRaises(IntegrityError):
                self.run_import(lambda: iter([(1, "new", "", "", "", "ACTIVO")]))

    def test_dry_run_deduplicates_without_writes(self):
        """Verifica que el modo dry-run simule la deduplicación sin escribir en la base de datos."""
        stdout, exported = self.run_import(
            lambda: iter([(1, "same", "", "", "", "ACTIVO"),
                          (2, "same", "", "", "", "ACTIVO")]),
            "--dry-run",
        )
        self.assertFalse(User.objects.exists())
        self.assertEqual(exported[1][1], "DRY_RUN")
        self.assertIn("Creados: 1. Actualizados: 0. Saltados: 1.", stdout)

    def test_existing_id_or_username_is_preserved_in_both_modes(self):
        """La caché inicial omite ambas identidades sin modificar usuarios existentes."""
        for options in ((), ("--dry-run",)):
            with self.subTest(options=options):
                self.setUp()
                existing = User.objects.create_user(
                    id=10, username="existing", password="original",
                    email="original@example.test", first_name="Original", is_active=False,
                )
                original_password = existing.password
                stdout, exported = self.run_import(
                    lambda: iter([
                        (10, "different", "new@example.test", "New", "Name", "ACTIVO"),
                        (11, " existing ", "new@example.test", "New", "Name", "ACTIVO"),
                    ]),
                    *options,
                )
                existing.refresh_from_db()
                self.assertEqual(User.objects.count(), 1)
                self.assertEqual(existing.username, "existing")
                self.assertEqual(existing.email, "original@example.test")
                self.assertEqual(existing.first_name, "Original")
                self.assertEqual(existing.password, original_password)
                self.assertFalse(existing.is_active)
                self.assertEqual(exported, [["username", "temp_password", "email"]])
                self.assertIn("Creados: 0. Actualizados: 0. Saltados: 2.", stdout)

    def test_source_duplicates_are_skipped_in_both_modes(self):
        """IDs repetidos y nombres normalizados se deduplican durante la misma carga."""
        for options in ((), ("--dry-run",)):
            with self.subTest(options=options):
                self.setUp()
                stdout, exported = self.run_import(
                    lambda: iter([
                        (1, " first ", " first@example.test ", " Ana ", " Pérez ", " activo "),
                        (1, "another", "", "", "", "ACTIVO"),
                        (2, "first", "", "", "", "ACTIVO"),
                        (3, "last", None, None, None, "INACTIVO"),
                    ]),
                    *options,
                )
                password = "DRY_RUN" if options else "first"
                self.assertEqual(exported, [
                    ["username", "temp_password", "email"],
                    ["first", password, "first@example.test"],
                    ["last", "DRY_RUN" if options else "last", ""],
                ])
                self.assertIn("Creados: 2. Actualizados: 0. Saltados: 2.", stdout)
                if options:
                    self.assertFalse(User.objects.exists())
                else:
                    self.assertEqual(User.objects.count(), 2)
                    first = User.objects.get(pk=1)
                    self.assertEqual((first.first_name, first.last_name), ("Ana", "Pérez"))
                    self.assertTrue(first.is_active)
                    self.assertTrue(first.check_password("first"))
                    last = User.objects.get(pk=3)
                    self.assertFalse(last.is_active)
                    self.assertEqual((last.first_name, last.last_name, last.email), ("", "", ""))
                    self.assertFalse(first.is_staff or first.is_superuser)

    def test_skipped_blank_username_does_not_reserve_id(self):
        """Una fila inválida no impide crear luego un usuario válido con el mismo ID."""
        for options in ((), ("--dry-run",)):
            with self.subTest(options=options):
                self.setUp()
                stdout, exported = self.run_import(
                    lambda: iter([
                        (1, None, "", "", "", "ACTIVO"),
                        (1, "   ", "", "", "", "ACTIVO"),
                        (1, "valid", "", "", "", "ACTIVO"),
                    ]),
                    *options,
                )
                self.assertEqual([row[0] for row in exported], ["username", "valid"])
                self.assertIn("Creados: 1. Actualizados: 0. Saltados: 2.", stdout)
                self.assertEqual(User.objects.count(), 0 if options else 1)

    def test_conflicting_row_does_not_reserve_its_other_identity(self):
        """Un conflicto concurrente no contamina la caché de identidades creadas."""
        def rows():
            User.objects.create(id=99, username="taken")
            yield (1, "taken", "", "", "", "ACTIVO")
            yield (1, "available", "", "", "", "ACTIVO")

        with transaction.atomic():
            stdout, exported = self.run_import(rows)
            self.assertTrue(User.objects.filter(pk=1, username="available").exists())
        self.assertEqual([row[0] for row in exported], ["username", "available"])
        self.assertIn("Creados: 1. Actualizados: 0. Saltados: 1.", stdout)

    def test_empty_source_exports_only_header(self):
        """Una fuente vacía produce un resumen y CSV válidos en ambos modos."""
        for options in ((), ("--dry-run",)):
            with self.subTest(options=options):
                stdout, exported = self.run_import(lambda: iter(()), *options, total_count=0)
                self.assertEqual(exported, [["username", "temp_password", "email"]])
                self.assertIn("Creados: 0. Actualizados: 0. Saltados: 0.", stdout)
                self.assertFalse(User.objects.exists())

    def test_unclassified_error_keeps_outer_transaction_usable(self):
        """El savepoint se revierte antes de propagar errores no reconocidos."""
        original_save = User.save

        def fail_with_null_email(user, **kwargs):
            user.email = None
            return original_save(user, **kwargs)

        with transaction.atomic():
            with patch.object(User, "save", autospec=True, side_effect=fail_with_null_email):
                with self.assertRaises(IntegrityError):
                    self.run_import(lambda: iter([(1, "new", "", "", "", "ACTIVO")]))
            self.assertFalse(User.objects.exists())
            User.objects.create(id=2, username="after-error")
            self.assertTrue(User.objects.filter(pk=2).exists())

    def test_mysql_constraint_classification(self):
        """Valida la clasificación de errores de unicidad específicos para MySQL."""
        for code, key, expected in (
            (1062, "PRIMARY", True),
            (1062, "username", True),
            (1062, "auth_user.username", True),
            (1062, "email", False),
            (1048, "username", False),
            (1062, "username_extra", False),
        ):
            with self.subTest(code=code, key=key):
                error = IntegrityError("insert failed")
                error.__cause__ = Exception(code, f"Duplicate entry 'value' for key '{key}'")
                self.assertEqual(sync.is_identity_conflict(error, "mysql"), expected)
        self.assertFalse(sync.is_identity_conflict(IntegrityError("unknown"), "mysql"))


class IdentityConflictTests(unittest.TestCase):
    """Clasificación conservadora de errores sin acceso a base de datos."""

    def test_sqlite_only_accepts_exact_identity_constraints(self):
        for message, expected in (
            ("UNIQUE constraint failed: auth_user.id", True),
            ("UNIQUE constraint failed: auth_user.username", True),
            ("UNIQUE constraint failed: auth_user.email", False),
            ("UNIQUE constraint failed: other_table.username", False),
            ("UNIQUE constraint failed: auth_user.username_extra", False),
            ("UNIQUE constraint failed: auth_user.id, auth_user.email", False),
            ("NOT NULL constraint failed: auth_user.username", False),
            ("FOREIGN KEY constraint failed", False),
        ):
            with self.subTest(message=message):
                error = IntegrityError("insert failed")
                error.__cause__ = sqlite3.IntegrityError(message)
                self.assertEqual(sync.is_identity_conflict(error, "sqlite"), expected)

    def test_mysql_quoting_qualification_and_malformed_errors(self):
        for args, expected in (
            ((1062, "Duplicate entry 'x' for key `auth_user.PRIMARY`"), True),
            ((1062, "Duplicate entry 'x' for key `username`"), True),
            ((1062, "Duplicate entry 'x' for key 'db.auth_user.username'"), True),
            ((1062, "Duplicate entry 'username' for key 'email'"), False),
            ((1062, "Duplicate entry 'x' for key 'username' extra"), False),
            ((1062, "Duplicate entry 'x' for key username"), False),
            ((1062, "unrecognized message"), False),
            ((1062,), False),
            ((), False),
            (("1062", "Duplicate entry 'x' for key 'username'"), False),
        ):
            with self.subTest(args=args):
                error = IntegrityError("insert failed")
                error.__cause__ = Exception(*args)
                self.assertEqual(sync.is_identity_conflict(error, "mysql"), expected)

    def test_missing_cause_and_unsupported_vendors_are_not_conflicts(self):
        for vendor in ("mysql", "sqlite", "postgresql", "oracle", ""):
            with self.subTest(vendor=vendor):
                self.assertFalse(sync.is_identity_conflict(IntegrityError("unknown"), vendor))
        error = IntegrityError("insert failed")
        error.__cause__ = sqlite3.IntegrityError("UNIQUE constraint failed: auth_user.id")
        self.assertFalse(sync.is_identity_conflict(error, "postgresql"))


if __name__ == "__main__":
    unittest.main()
