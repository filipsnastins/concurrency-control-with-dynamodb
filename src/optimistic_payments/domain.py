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

    @staticmethod
    def create(customer_id: str, amount: int, currency: str) -> "PaymentIntent":
        return PaymentIntent(
            id=str(uuid.uuid4()),
            state=PaymentIntentState.CREATED,
            customer_id=customer_id,
            amount=amount,
            currency=currency,
            version=0,
        )

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
