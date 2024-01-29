from typing import Protocol

from ..domain import PaymentIntent
from .dynamodb import DynamoDBPaymentIntentRepository
from .exceptions import OptimisticLockError

__all__ = [
    "DynamoDBPaymentIntentRepository",
    "OptimisticLockError",
    "PaymentIntentRepository",
]


class PaymentIntentRepository(Protocol):
    async def get(self, payment_intent_id: str) -> PaymentIntent:
        ...  # pragma: no cover

    async def create(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover

    async def update(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover
