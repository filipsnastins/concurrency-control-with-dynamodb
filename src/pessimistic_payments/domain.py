import uuid
from dataclasses import dataclass
from enum import StrEnum

from .payment_gateway import PaymentGateway


class PaymentIntentNotFoundError(Exception):
    pass


class PaymentIntentStateError(Exception):
    pass


class PaymentIntentState(StrEnum):
    CREATED = "CREATED"
    CHARGED = "CHARGED"
    CHARGE_FAILED = "CHARGE_FAILED"


@dataclass
class Charge:
    id: str
    error_code: str | None
    error_message: str | None


class PaymentIntent:
    def __init__(
        self,
        id: str,
        state: PaymentIntentState,
        customer_id: str,
        amount: int,
        currency: str,
        charge: Charge | None,
    ) -> None:
        self._id = id
        self._state = state
        self._customer_id = customer_id
        self._amount = amount
        self._currency = currency
        self._charge = charge

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

    @property
    def charge(self) -> Charge | None:
        return self._charge

    @staticmethod
    def create(customer_id: str, amount: int, currency: str) -> "PaymentIntent":
        return PaymentIntent(
            id=f"pi_{uuid.uuid4()}",
            state=PaymentIntentState.CREATED,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            charge=None,
        )

    async def execute_charge(self, payment_gateway: PaymentGateway) -> None:
        if self._state != PaymentIntentState.CREATED:
            raise PaymentIntentStateError(f"PaymentIntent is not in a chargeable state: {self._state}")

        response = await payment_gateway.charge(self._id, self._amount, self._currency)
        if response.error_code is not None:
            self._state = PaymentIntentState.CHARGE_FAILED
        else:
            self._state = PaymentIntentState.CHARGED

        self._charge = Charge(
            id=response.id,
            error_code=response.error_code,
            error_message=response.error_message,
        )

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, PaymentIntent):
            raise NotImplementedError  # pragma: no cover
        return (
            self._id == __value._id
            and self._state == __value._state
            and self._customer_id == __value._customer_id
            and self._amount == __value._amount
            and self._currency == __value._currency
        )
