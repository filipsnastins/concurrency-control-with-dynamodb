import pytest
from botocore.exceptions import ClientError

from pessimistic_payments.domain import Charge, PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState
from pessimistic_payments.repository import DynamoDBPaymentIntentRepository


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await repo.get("pi_123456")


@pytest.mark.parametrize(
    "charge",
    [
        None,
        Charge(id="ch_123456", error_code=None, error_message=None),
        Charge(id="ch_123456", error_code="card_declined", error_message="Insufficient funds."),
    ],
)
@pytest.mark.asyncio()
async def test_create_and_get_payment_intent(repo: DynamoDBPaymentIntentRepository, charge: Charge | None) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=charge,
    )

    await repo.create(payment_intent)

    assert await repo.get(payment_intent.id) == payment_intent


@pytest.mark.asyncio()
async def test_should_raise_on_already_existing_payment_intent_id(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
    )

    await repo.create(payment_intent)

    with pytest.raises(ClientError):
        await repo.create(payment_intent)


@pytest.mark.parametrize(
    "charge",
    [
        None,
        Charge(id="ch_123456", error_code=None, error_message=None),
        Charge(id="ch_123456", error_code="card_declined", error_message="Insufficient funds."),
    ],
)
@pytest.mark.asyncio()
async def test_update_payment_intent(repo: DynamoDBPaymentIntentRepository, charge: Charge | None) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=Charge(id="ch_999999", error_code=None, error_message=None),
    )
    await repo.create(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_999999",
        amount=1481850,
        currency="JPY",
        charge=charge,
    )
    await repo.update(payment_intent)

    assert await repo.get(payment_intent.id) == PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=charge,
    )


@pytest.mark.asyncio()
async def test_should_raise_on_not_existing_payment_intent_update(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
    )

    with pytest.raises(PaymentIntentNotFoundError, match=payment_intent.id):
        await repo.update(payment_intent)

    with pytest.raises(PaymentIntentNotFoundError, match=payment_intent.id):
        await repo.get(payment_intent.id)
