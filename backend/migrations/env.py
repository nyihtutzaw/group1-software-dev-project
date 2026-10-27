from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine

from app.core.config import get_settings
from app.core.db import Base
from app.core.models_registry import import_all_models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import_all_models()
target_metadata = Base.metadata

# PostGIS ships its own tables (e.g. spatial_ref_sys); never let autogenerate drop them.
POSTGIS_TABLES = {"spatial_ref_sys"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and name in POSTGIS_TABLES:
        return False
    return alembic_helpers.include_object(obj, name, type_, reflected, compare_to)


def run_migrations() -> None:
    url = config.attributes.get("database_url") or get_settings().database_url
    connectable = create_engine(url)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            # GeoAlchemy2 helpers: render Geometry columns and spatial indexes correctly
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
