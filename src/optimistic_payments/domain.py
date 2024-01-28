import uuid
from enum import StrEnum


class PaymentIntentNotFoundError(Exception):
    pass


class PaymentIntentStateError(Exception):
    pass


class PaymentIntentState(StrEnum):
    CREATED = "CREATED"
    CHARGE_REQUESTED = "CHARGE_REQUESTED"
    CHARGED = "CHARGED"
    CHARGE_FAILED = "CHARGE_FAILED"


class PaymentIntent:
    def __init__(
        self, id: str, state: PaymentIntentState, customer_id: str, amount: int, currency: str, version: int
    ) -> None:
        self._id = id
        self._state = state
        self._customer_id = customer_id
        self._amount = amount
        self._currency = currency
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
            version=0,
        )

    def change_amount(self, amount: int) -> None:
        if self._state != PaymentIntentState.CREATED:
            raise PaymentIntentStateError(f"Cannot change PaymentIntent amount in state: {self._state}")
        self._amount = amount

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, PaymentIntent):
            return False
        return (
            self._id == __value._id
            and self._state == __value._state
            and self._customer_id == __value._customer_id
            and self._amount == __value._amount
            and self._currency == __value._currency
            and self._version == __value._version
        )
