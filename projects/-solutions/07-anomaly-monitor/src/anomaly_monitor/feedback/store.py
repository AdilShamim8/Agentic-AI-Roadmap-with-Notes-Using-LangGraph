"""Feedback store — SQLite-backed persistence for operator feedback.

Uses SQLAlchemy 2.0 async style with the aiosqlite driver. All operations are
best-effort: errors are logged via structlog and never raised, so a failure in
the feedback store can never break the main anomaly-detection pipeline.

Degrades gracefully to a no-op store when SQLAlchemy / aiosqlite are missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import structlog

from anomaly_monitor.config import Settings
from anomaly_monitor.models import Feedback

log = structlog.get_logger()

# Lazy-import heavy deps at module top-level; degrade if unavailable.
try:  # pragma: no cover - exercised only in environments without sqlalchemy
    from sqlalchemy import Boolean, Float, Integer, String, Text, func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

    _HAS_SQLA = True
except ImportError:  # pragma: no cover
    _HAS_SQLA = False
    log.warning("sqlalchemy_unavailable_feedback_store_degraded")


if _HAS_SQLA:

    class _Base(DeclarativeBase):
        """Declarative base for the feedback store."""

    class FeedbackORM(_Base):
        """SQLAlchemy ORM mirror of the `Feedback` pydantic model."""

        __tablename__ = "feedback"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        anomaly_id: Mapped[str] = mapped_column(String(255), index=True)
        is_real_anomaly: Mapped[bool] = mapped_column(Boolean)
        action_correct: Mapped[Optional[bool]] = mapped_column(
            Boolean, nullable=True
        )
        operator_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        created_at: Mapped[float] = mapped_column(Float, index=True)


def _orm_to_feedback(orm: "FeedbackORM") -> Feedback:
    """Convert an ORM row to a `Feedback` pydantic instance."""
    return Feedback(
        anomaly_id=orm.anomaly_id,
        is_real_anomaly=orm.is_real_anomaly,
        action_correct=orm.action_correct,
        operator_note=orm.operator_note,
        created_at=orm.created_at,
    )


class FeedbackStore:
    """Async SQLite feedback store. Best-effort: never raises."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._engine: Optional[Any] = None
        self._sessionmaker: Optional[Any] = None
        self._started: bool = False

    async def start(self) -> None:
        """Initialise engine + create tables if not exist."""
        if not _HAS_SQLA:
            log.warning("feedback_store_start_skipped_sqlalchemy_unavailable")
            return
        if self._started:
            return
        try:
            db_path = Path(self._settings.feedback_db)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            # SQLite path: relative resolves against CWD; use absolute for clarity.
            engine_url = "sqlite+aiosqlite:///" + str(db_path)
            self._engine = create_async_engine(engine_url, future=True)
            self._sessionmaker = async_sessionmaker(
                self._engine, expire_on_commit=False
            )
            async with self._engine.begin() as conn:
                await conn.run_sync(_Base.metadata.create_all)
            self._started = True
            log.info("feedback_store_started", db=str(db_path))
        except Exception as e:  # pragma: no cover - defensive
            log.error("feedback_store_start_failed", error=str(e))
            self._engine = None
            self._sessionmaker = None
            self._started = False

    async def record(self, feedback: Feedback) -> int:
        """Persist a Feedback row, return its id (0 on failure)."""
        if not self._started or self._sessionmaker is None:
            return 0
        try:
            async with self._sessionmaker() as session:
                orm = FeedbackORM(
                    anomaly_id=feedback.anomaly_id,
                    is_real_anomaly=feedback.is_real_anomaly,
                    action_correct=feedback.action_correct,
                    operator_note=feedback.operator_note,
                    created_at=feedback.created_at,
                )
                session.add(orm)
                await session.commit()
                await session.refresh(orm)
                return int(orm.id or 0)
        except Exception as e:  # pragma: no cover - defensive
            log.error("feedback_record_failed", error=str(e))
            return 0

    async def get(self, anomaly_id: str) -> Optional[Feedback]:
        """Fetch the most-recent feedback for an anomaly (highest id)."""
        if not self._started or self._sessionmaker is None:
            return None
        try:
            async with self._sessionmaker() as session:
                stmt = (
                    select(FeedbackORM)
                    .where(FeedbackORM.anomaly_id == anomaly_id)
                    .order_by(FeedbackORM.id.desc())
                    .limit(1)
                )
                orm = (await session.execute(stmt)).scalar_one_or_none()
                return _orm_to_feedback(orm) if orm is not None else None
        except Exception as e:  # pragma: no cover - defensive
            log.error("feedback_get_failed", error=str(e))
            return None

    async def recent(self, limit: int = 100) -> list[Feedback]:
        """Recent feedback rows (newest first)."""
        if not self._started or self._sessionmaker is None:
            return []
        try:
            async with self._sessionmaker() as session:
                stmt = (
                    select(FeedbackORM)
                    .order_by(FeedbackORM.id.desc())
                    .limit(limit)
                )
                rows = (await session.execute(stmt)).scalars().all()
                return [_orm_to_feedback(r) for r in rows]
        except Exception as e:  # pragma: no cover - defensive
            log.error("feedback_recent_failed", error=str(e))
            return []

    async def stats(self) -> dict[str, Any]:
        """Aggregate stats: total, real_pct, action_correct_pct, by_kind {...}.

        ``by_kind`` breaks down counts by ``is_real_anomaly`` and
        ``action_correct`` status. Returns 0/empty on failure. Note: return
        type is ``dict[str, Any]`` (not ``dict[str, float]``) because
        ``by_kind`` is a nested dict.
        """
        empty: dict[str, Any] = {
            "total": 0.0,
            "real_pct": 0.0,
            "action_correct_pct": 0.0,
            "by_kind": {},
        }
        if not self._started or self._sessionmaker is None:
            return empty
        try:
            async with self._sessionmaker() as session:
                total = (
                    await session.execute(
                        select(func.count()).select_from(FeedbackORM)
                    )
                ).scalar_one()
                if not total:
                    return empty
                real = (
                    await session.execute(
                        select(func.count())
                        .select_from(FeedbackORM)
                        .where(FeedbackORM.is_real_anomaly == True)  # noqa: E712
                    )
                ).scalar_one()
                correct = (
                    await session.execute(
                        select(func.count())
                        .select_from(FeedbackORM)
                        .where(FeedbackORM.action_correct == True)  # noqa: E712
                    )
                ).scalar_one()
                incorrect = (
                    await session.execute(
                        select(func.count())
                        .select_from(FeedbackORM)
                        .where(FeedbackORM.action_correct == False)  # noqa: E712
                    )
                ).scalar_one()
                no_opinion = total - correct - incorrect
                return {
                    "total": float(total),
                    "real_pct": real / total,
                    "action_correct_pct": correct / total,
                    "by_kind": {
                        "real_anomaly": float(real),
                        "false_alarm": float(total - real),
                        "action_correct_true": float(correct),
                        "action_correct_false": float(incorrect),
                        "action_correct_none": float(no_opinion),
                    },
                }
        except Exception as e:  # pragma: no cover - defensive
            log.error("feedback_stats_failed", error=str(e))
            return empty

    async def aclose(self) -> None:
        """Dispose of the engine. Safe to call multiple times."""
        if self._engine is not None:
            try:
                await self._engine.dispose()
            except Exception as e:  # pragma: no cover - defensive
                log.error("feedback_store_close_failed", error=str(e))
        self._engine = None
        self._sessionmaker = None
        self._started = False
