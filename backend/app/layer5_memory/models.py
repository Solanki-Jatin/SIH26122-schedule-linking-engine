"""
Layer 5: Institutional memory - data model.

Every confirmed actual update from layer 4 becomes one ConfirmedEvent
row here. This is intentionally an append-only log of what actually
happened, not just a mirror of current schedule state, so that patterns
can be queried across projects after closure (e.g. "average delay for
civil foundation work"), which is the PS's explicit ask for turning
execution history into institutional memory.

Built against SQLAlchemy so the same models work with SQLite (prototype/
demo) and PostgreSQL (production) by only changing the connection
string. See docs/architecture.md section 5 for the reasoning.
"""

from datetime import date, datetime, UTC

from sqlalchemy import Float, String, Date, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ConfirmedEvent(Base):
    """
    One confirmed actual execution event for one task on one project.

    delay_days is signed: positive means the task finished later than
    planned, negative means early, zero means on time. Computed once at
    write time from planned vs actual duration, never recomputed
    silently later, so historical queries stay stable even if CPM logic
    changes in future versions.
    """

    __tablename__ = "confirmed_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(64))
    task_id: Mapped[str] = mapped_column(String(64))
    task_name: Mapped[str] = mapped_column(String(256))
    discipline: Mapped[str] = mapped_column(String(64))

    planned_duration_days: Mapped[int]
    actual_duration_days: Mapped[int]
    delay_days: Mapped[int]

    confidence: Mapped[float] = mapped_column(Float)
    matched_by: Mapped[str] = mapped_column(String(16))  # "auto" or "manual"
    source_text: Mapped[str] = mapped_column(String(512))

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    closed_date: Mapped[date] = mapped_column(Date)
