from dataclasses import dataclass
from typing import Protocol


class PaymentGateway(Protocol):
    async def charge(self, payment_intent_id: str, amount: int, currency: str) -> "PaymentGatewayResponse":
        ...  # pragma: no cover


@dataclass
class PaymentGatewayResponse:
    id: str
    error_code: str | None = None
    error_message: str | None = None
