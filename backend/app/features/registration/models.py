"""F1 Project registration & evidence — database tables.

MINIMAL STUB added by F2 so boundaries have a project to belong to. F1 owns this table:
extend it with the registration fields (methodology, crediting period, baseline, additionality, …)
and the evidence tables. Keep `id`, `code`, `name`, `owner_id` and `created_at` — F2 relies on them.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Public registry ID shown everywhere, e.g. CRVR-0147
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
