from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from typing import Any, Protocol
from confluent_kafka import Producer

logger = logging.getLogger(__name__)

class EventProducer(Protocol):
    def publish(self, event_type: str, payload: dict[str, Any]) -> None: ...
    def close(self) -> None: ...

class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str, client_id: str, topic: str) -> None:
        self._topic = topic
        self._producer = Producer({"bootstrap.servers": bootstrap_servers, "client.id": client_id})
    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        envelope = {"event_type": event_type, "occurred_at": datetime.now(UTC).isoformat(), "payload": payload}
        try:
            self._producer.produce(self._topic, json.dumps(envelope, default=str).encode())
            self._producer.poll(0)
        except BufferError:
            logger.warning("Kafka delivery queue full", extra={"event_type": event_type})
    def close(self) -> None:
        self._producer.flush(5)

class NullEventProducer:
    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        logger.warning("Event producer unavailable", extra={"event_type": event_type})
    def close(self) -> None: pass
