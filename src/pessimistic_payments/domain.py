import uuid
from enum import StrEnum

from .payment_gateway import PaymentGateway, PaymentGatewayError


class PaymentIntentNotFoundError(Exception):
    pass


class PaymentIntentStateError(Exception):
    pass


class PaymentIntentState(StrEnum):
    CREATED = "CREATED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PaymentIntent:
    def __init__(self, id: str, state: PaymentIntentState, customer_id: str, amount: int, currency: str) -> None:
        self.id = id
        self.state = state
        self.customer_id = customer_id
        self.amount = amount
        self.currency = currency

    @staticmethod
    def create(customer_id: str, amount: int, currency: str) -> "PaymentIntent":
        return PaymentIntent(
            id=str(uuid.uuid4()),
            state=PaymentIntentState.CREATED,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
        )

    async def charge(self, payment_gateway: PaymentGateway) -> None:
        if self.state != PaymentIntentState.CREATED:
            raise PaymentIntentStateError(f"PaymentIntent is not in a chargeable state: {self.state}")
        try:
            await payment_gateway.charge(self.id, self.amount, self.currency)
        except PaymentGatewayError:
            self.state = PaymentIntentState.FAILED
        else:
            self.state = PaymentIntentState.SUCCEEDED
