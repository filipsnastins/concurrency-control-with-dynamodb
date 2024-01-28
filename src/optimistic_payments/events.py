import abc
import uuid
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class PaymentIntentEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    payment_intent_id: str

    @abc.abstractmethod
    def to_dict(self) -> dict:
        pass  # pragma: no cover


@dataclass(kw_only=True)
class PaymentIntentChargeRequested(PaymentIntentEvent):
    name: str = "PaymentIntentChargeRequested"
    amount: int
    currency: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "payment_intent_id": self.payment_intent_id,
            "amount": self.amount,
            "currency": self.currency,
        }
