"""Kafka-backed stream consumer built on :mod:`aiokafka`.

``aiokafka`` is imported lazily inside the class so that the rest of the
project (and the test suite) can run without the optional dependency
installed — only callers that actually instantiate
:class:`KafkaStreamConsumer` need it.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional

import structlog

from anomaly_monitor.config import Settings, settings as _default_settings
from anomaly_monitor.models import Event
from anomaly_monitor.streaming.base import StreamConsumer

log = structlog.get_logger()


class KafkaStreamConsumer(StreamConsumer):
    """Asynchronously consume :class:`Event` JSON payloads from a Kafka topic.

    Each Kafka message's ``value`` is expected to be a UTF-8 JSON document
    conforming to the :class:`Event` schema. Malformed messages are logged
    and skipped (the stream is never killed by a single bad record).
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Create a consumer. ``settings`` defaults to the global settings."""
        self._settings = settings or _default_settings
        self._consumer: Optional[Any] = None  # aiokafka.AIOKafkaConsumer
        self._started = False

    async def _ensure_started(self) -> Any:
        """Lazily create and start the underlying ``AIOKafkaConsumer``."""
        if self._consumer is not None:
            return self._consumer
        # Lazy import so aiokafka is only required when Kafka mode is used.
        from aiokafka import AIOKafkaConsumer  # type: ignore

        s = self._settings
        self._consumer = AIOKafkaConsumer(
            s.kafka_topic,
            bootstrap_servers=s.kafka_bootstrap_servers,
            group_id=s.kafka_consumer_group,
            auto_offset_reset=s.kafka_auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda v: v.decode("utf-8") if v else "",
        )
        await self._consumer.start()
        self._started = True
        log.info(
            "kafka_consumer_started",
            topic=s.kafka_topic,
            bootstrap=s.kafka_bootstrap_servers,
            group=s.kafka_consumer_group,
        )
        return self._consumer

    async def events(self) -> AsyncIterator[Event]:
        """Yield :class:`Event` objects from Kafka indefinitely.

        Deserialisation errors are logged and the offending message is
        skipped; the stream continues.
        """
        consumer = await self._ensure_started()
        assert consumer is not None
        try:
            async for msg in consumer:
                if msg.value is None:
                    continue
                try:
                    yield Event.model_validate_json(msg.value)
                except Exception as exc:  # noqa: BLE001 — must not kill stream
                    log.warning(
                        "kafka_deserialise_failed",
                        error=str(exc),
                        partition=msg.partition,
                        offset=msg.offset,
                    )
                    continue
        finally:
            log.info("kafka_consumer_stream_end")

    async def aclose(self) -> None:
        """Stop the underlying Kafka consumer (idempotent)."""
        if self._consumer is not None and self._started:
            try:
                await self._consumer.stop()
                log.info("kafka_consumer_stopped")
            except Exception as exc:  # noqa: BLE001
                log.warning("kafka_consumer_stop_failed", error=str(exc))
            finally:
                self._started = False
                self._consumer = None
