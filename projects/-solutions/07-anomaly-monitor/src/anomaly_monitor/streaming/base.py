"""Abstract base class for all stream consumers.

A :class:`StreamConsumer` is an async, async-context-manager source of
:class:`anomaly_monitor.models.Event` objects. Implementations include
Kafka, a synthetic Poisson generator, and a JSONL file replay source.
"""

from __future__ import annotations

import abc
from typing import AsyncIterator

from anomaly_monitor.models import Event


class StreamConsumer(abc.ABC):
    """Async stream of :class:`Event` objects.

    Subclasses implement :meth:`events` (an async generator yielding events)
    and :meth:`aclose` (releases any underlying resources such as a Kafka
    consumer, file handle, etc). The class also works as an async context
    manager so callers can write::

        async with KafkaStreamConsumer() as src:
            async for ev in src.events():
                ...
    """

    @abc.abstractmethod
    async def events(self) -> AsyncIterator[Event]:
        """Yield :class:`Event` objects until the stream is exhausted or closed."""
        ...
        # Required to make this an async generator; never executed.
        yield  # pragma: no cover
        return  # pragma: no cover

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release any resources held by this consumer."""
        ...

    async def __aenter__(self) -> StreamConsumer:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
