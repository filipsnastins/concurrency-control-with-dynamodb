import uuid
from dataclasses import dataclass
from enum import StrEnum

from .events import PaymentIntentChargeRequested, PaymentIntentEvent


class PaymentIntentNotFoundError(Exception):
    pass


class PaymentIntentStateError(Exception):
    pass


class PaymentIntentState(StrEnum):
    CREATED = "CREATED"
    CHARGE_REQUESTED = "CHARGE_REQUESTED"
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
        events: list[PaymentIntentEvent],
        version: int,
    ) -> None:
        self._id = id
        self._state = state
        self._customer_id = customer_id
        self._amount = amount
        self._currency = currency
        self._charge = charge
        self._events = events
        self._version = version

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

    @property
    def events(self) -> list[PaymentIntentEvent]:
        return self._events

    @property
    def version(self) -> int:
        return self._version

    @staticmethod
    def create(customer_id: str, amount: int, currency: str) -> "PaymentIntent":
        return PaymentIntent(
            id=f"pi_{uuid.uuid4()}",
            state=PaymentIntentState.CREATED,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            charge=None,
            events=[],
            version=0,
        )

    def change_amount(self, amount: int) -> None:
        if self._state != PaymentIntentState.CREATED:
            raise PaymentIntentStateError(f"Cannot change PaymentIntent amount in state: {self._state}")

        self._amount = amount

    def request_charge(self) -> None:
        if self._state != PaymentIntentState.CREATED:
            raise PaymentIntentStateError(f"Cannot charge PaymentIntent in state: {self._state}")

        self._state = PaymentIntentState.CHARGE_REQUESTED

        event = PaymentIntentChargeRequested(
            payment_intent_id=self._id,
            amount=self._amount,
            currency=self._currency,
        )
        self._events.append(event)

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, PaymentIntent):
            raise NotImplementedError  # pragma: no cover
        return (
            self._id == __value._id
            and self._state == __value._state
            and self._customer_id == __value._customer_id
            and self._amount == __value._amount
            and self._currency == __value._currency
            and self._charge == __value._charge
            and self._version == __value._version
        )
