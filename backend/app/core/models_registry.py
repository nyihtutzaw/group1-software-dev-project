"""Import every models module so Base.metadata knows all tables.

Used by Alembic and the test suite. New feature models are found automatically —
no need to edit this file when you add one.
"""

import importlib
import pkgutil

import app.features


def import_all_models() -> None:
    importlib.import_module("app.auth.models")
    for feature in pkgutil.iter_modules(app.features.__path__):
        try:
            importlib.import_module(f"app.features.{feature.name}.models")
        except ModuleNotFoundError as exc:
            if exc.name != f"app.features.{feature.name}.models":
                raise
