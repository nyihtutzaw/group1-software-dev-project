"""Wipe the hosted demo database so it can be migrated and seeded again from scratch.

Run only through `scripts/cloud-run-job.sh reset` (the "Reset demo data" GitHub Action). It refuses
unless demo accounts are enabled (development, or production with DEMO_MODE=true), so it can never
touch a real registry. Dropping the whole `public` schema also removes the trigger functions, enum
types and the PostGIS extension, which the migrations then create again.

Evidence files in the storage bucket are left alone: they are write-once and the fresh seed simply
stops referring to them.
"""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine


def reset_demo_database() -> None:
    if not get_settings().demo_enabled:
        raise RuntimeError("Reset is only for demo data (development, or DEMO_MODE=true)")
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


if __name__ == "__main__":
    reset_demo_database()
    print("reset: demo database wiped")
