import uuid
from enum import StrEnum

from .payment_gateway import PaymentGateway, PaymentGatewayError


class PaymentIntentNotFoundError(Exception):
    pass


class PaymentIntentStateError(Exception):
    pass


class PaymentIntentState(StrEnum):
    CREATED = "CREATED"
    CHARGED = "CHARGED"
    CHARGE_FAILED = "CHARGE_FAILED"


class PaymentIntent:
    def __init__(self, id: str, state: PaymentIntentState, customer_id: str, amount: int, currency: str) -> None:
        self._id = id
        self._state = state
        self._customer_id = customer_id
        self._amount = amount
        self._currency = currency

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> PaymentIntentState:
        return self._state

    @property
    def customer_id(self) -> str:
        return self._customer_id

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency

    @staticmethod
    def create(customer_id: str, amount: int, currency: str) -> "PaymentIntent":
        return PaymentIntent(
            id=f"pi_{uuid.uuid4()}",
            state=PaymentIntentState.CREATED,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
        )

    async def charge(self, payment_gateway: PaymentGateway) -> None:
        if self._state != PaymentIntentState.CREATED:
            raise PaymentIntentStateError(f"PaymentIntent is not in a chargeable state: {self._state}")
        try:
            await payment_gateway.charge(self._id, self._amount, self._currency)
        except PaymentGatewayError:
            self._state = PaymentIntentState.CHARGE_FAILED
        else:
            self._state = PaymentIntentState.CHARGED
