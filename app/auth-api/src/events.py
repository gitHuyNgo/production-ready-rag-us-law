"""
Pub/sub for auth-api: UserCreated events.
Uses Kafka when KAFKA_BOOTSTRAP_SERVERS is set; otherwise in-memory (tests/local).
"""
import json
import logging
from dataclasses import asdict, dataclass

from typing import List, Optional

from src.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class UserCreatedEvent:
    user_id: str
    username: str
    email: str


class InMemoryEventPublisher:
    """In-memory publisher used when Kafka is not configured."""

    def __init__(self) -> None:
        self.published: List[UserCreatedEvent] = []

    async def publish_user_created(self, event: UserCreatedEvent) -> None:
        self.published.append(event)
        logger.info("UserCreated event published (in-memory): %s", asdict(event))


class KafkaEventPublisher:
    """Publish UserCreated to Kafka."""

    def __init__(self) -> None:
        self._producer = None

    async def _get_producer(self):
        if self._producer is not None:
            return self._producer
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError:
            logger.warning("aiokafka not installed; UserCreated will not be sent to Kafka")
            return None
        bootstrap = (settings.KAFKA_BOOTSTRAP_SERVERS or "").strip()
        if not bootstrap:
            return None
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        return self._producer

    async def publish_user_created(self, event: UserCreatedEvent) -> None:
        producer = await self._get_producer()
        if producer is None:
            logger.debug("Kafka not configured; skipping UserCreated publish")
            return
        topic = settings.KAFKA_USER_CREATED_TOPIC or "user.created"
        payload = asdict(event)
        try:
            await producer.send_and_wait(topic, value=payload)
            logger.info("UserCreated event sent to Kafka topic %s: %s", topic, payload)
        except Exception as e:
            logger.exception("Failed to send UserCreated to Kafka: %s", e)

    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None


def get_publisher() -> InMemoryEventPublisher | KafkaEventPublisher:
    """Use Kafka if KAFKA_BOOTSTRAP_SERVERS is set; else in-memory."""
    if (settings.KAFKA_BOOTSTRAP_SERVERS or "").strip():
        return KafkaEventPublisher()
    return InMemoryEventPublisher()


# Global instance; main.py may replace with Kafka in lifespan.
publisher: InMemoryEventPublisher | KafkaEventPublisher = InMemoryEventPublisher()
