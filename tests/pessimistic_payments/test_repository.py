import pytest

from pessimistic_payments.domain import PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState
from pessimistic_payments.repository import DynamoDBPaymentIntentRepository, PaymentIntentIdentifierCollisionError


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = await repo.get("123456")

    assert payment_intent is None


@pytest.mark.asyncio()
async def test_create_and_get_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi-123456",
        state=PaymentIntentState.CREATED,
        customer_id="customer-123456",
        amount=100,
        currency="USD",
    )

    await repo.create(payment_intent)

    db_payment_intent = await repo.get(payment_intent.id)
    assert db_payment_intent
    assert db_payment_intent.id == "pi-123456"
    assert db_payment_intent.state == PaymentIntentState.CREATED
    assert db_payment_intent.customer_id == "customer-123456"
    assert db_payment_intent.amount == 100
    assert db_payment_intent.currency == "USD"


@pytest.mark.asyncio()
async def test_should_raise_on_already_existing_payment_intent_id(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi-123456",
        state=PaymentIntentState.CREATED,
        customer_id="customer-123456",
        amount=100,
        currency="USD",
    )

    await repo.create(payment_intent)

    with pytest.raises(PaymentIntentIdentifierCollisionError, match=payment_intent.id):
        await repo.create(payment_intent)


@pytest.mark.asyncio()
async def test_update_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi-123456",
        state=PaymentIntentState.CREATED,
        customer_id="customer-123456",
        amount=100,
        currency="USD",
    )
    await repo.create(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.SUCCEEDED,
        customer_id="customer-999999",
        amount=1481850,
        currency="JPY",
    )
    await repo.update(payment_intent)

    db_payment_intent = await repo.get(payment_intent.id)
    assert db_payment_intent
    assert db_payment_intent.id == "pi-123456"
    assert db_payment_intent.state == PaymentIntentState.SUCCEEDED
    assert db_payment_intent.customer_id == "customer-123456"
    assert db_payment_intent.amount == 100
    assert db_payment_intent.currency == "USD"


@pytest.mark.asyncio()
async def test_should_raise_on_not_existing_payment_intent_update(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi-123456",
        state=PaymentIntentState.CREATED,
        customer_id="customer-123456",
        amount=100,
        currency="USD",
    )

    with pytest.raises(PaymentIntentNotFoundError, match=payment_intent.id):
        await repo.update(payment_intent)

    assert await repo.get("123456") is None
