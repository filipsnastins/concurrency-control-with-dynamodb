from dataclasses import dataclass
from typing import Protocol


class PaymentGateway(Protocol):
    async def charge(self, payment_intent_id: str, amount: int, currency: str) -> None:
        ...  # pragma: no cover


@dataclass
class PaymentGatewayErrorResponse:
    error_code: str
    error_message: str


class PaymentGatewayError(Exception):
    def __init__(self, response: PaymentGatewayErrorResponse) -> None:
        self.response = response
