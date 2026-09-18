"""
Layer 5: Institutional memory - store and query logic.

Wraps the ConfirmedEvent model with a small, explicit API: record one
event, query aggregates. Every query is a real aggregate over whatever
rows actually exist. When there is no data for a query, this returns an
explicit "no data" result rather than a fabricated or default number,
because a silent zero or a made-up placeholder would be indistinguishable
from a real measured zero-delay average, which is exactly the kind of
fake-precision mistake the team has committed to avoiding.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import Base, ConfirmedEvent


@dataclass
class DisciplineDelayStats:
    discipline: str
    sample_size: int
    avg_delay_days: float | None  # None if sample_size == 0, never faked
    max_delay_days: int | None
    min_delay_days: int | None


class InstitutionalMemory:
    def __init__(self, db_url: str = "sqlite:///institutional_memory.db"):
        """
        db_url defaults to a local SQLite file for the prototype/demo.
        For production, pass a PostgreSQL URL
        (e.g. 'postgresql://user:pass@host/dbname'), same models apply
        unchanged.
        """
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)

    def record_event(
        self,
        project_id: str,
        task_id: str,
        task_name: str,
        discipline: str,
        planned_duration_days: int,
        actual_duration_days: int,
        confidence: float,
        matched_by: str,
        source_text: str,
        closed_date: date,
    ) -> ConfirmedEvent:
        event = ConfirmedEvent(
            project_id=project_id,
            task_id=task_id,
            task_name=task_name,
            discipline=discipline,
            planned_duration_days=planned_duration_days,
            actual_duration_days=actual_duration_days,
            delay_days=actual_duration_days - planned_duration_days,
            confidence=confidence,
            matched_by=matched_by,
            source_text=source_text,
            closed_date=closed_date,
        )
        with Session(self.engine) as session:
            session.add(event)
            session.commit()
            session.refresh(event)
        return event

    def query_delay_by_discipline(self, discipline: str) -> DisciplineDelayStats:
        """
        Real aggregate over confirmed_events for one discipline. Returns
        avg/max/min as None (not 0) when sample_size is 0, so a caller
        can never mistake 'no data' for a measured zero-delay result.
        """
        with Session(self.engine) as session:
            stmt = select(ConfirmedEvent.delay_days).where(
                ConfirmedEvent.discipline == discipline
            )
            delays = [row[0] for row in session.execute(stmt).all()]

        if not delays:
            return DisciplineDelayStats(
                discipline=discipline,
                sample_size=0,
                avg_delay_days=None,
                max_delay_days=None,
                min_delay_days=None,
            )

        return DisciplineDelayStats(
            discipline=discipline,
            sample_size=len(delays),
            avg_delay_days=round(sum(delays) / len(delays), 2),
            max_delay_days=max(delays),
            min_delay_days=min(delays),
        )

    def all_disciplines_summary(self) -> list[DisciplineDelayStats]:
        """Same aggregate, broken out per discipline present in the store."""
        with Session(self.engine) as session:
            stmt = select(ConfirmedEvent.discipline).distinct()
            disciplines = [row[0] for row in session.execute(stmt).all()]
        return [self.query_delay_by_discipline(d) for d in disciplines]

    def event_count(self) -> int:
        with Session(self.engine) as session:
            return session.execute(
                select(func.count()).select_from(ConfirmedEvent)
            ).scalar_one()
