import pytest

from optimistic_payments.domain import PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState
from optimistic_payments.repository import (
    DynamoDBPaymentIntentRepository,
    OptimisticLockError,
    PaymentIntentIdentifierCollisionError,
)


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = await repo.get("123456")

    assert payment_intent is None


@pytest.mark.asyncio()
async def test_create_and_get_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )

    await repo.create(payment_intent)

    db_payment_intent = await repo.get(payment_intent.id)
    assert db_payment_intent
    assert db_payment_intent.id == "pi_123456"
    assert db_payment_intent.state == PaymentIntentState.CREATED
    assert db_payment_intent.customer_id == "cust_123456"
    assert db_payment_intent.amount == 100
    assert db_payment_intent.currency == "USD"
    assert db_payment_intent.version == 0


@pytest.mark.asyncio()
async def test_should_raise_on_already_existing_payment_intent_id(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )

    await repo.create(payment_intent)

    with pytest.raises(PaymentIntentIdentifierCollisionError, match=payment_intent.id):
        await repo.create(payment_intent)


@pytest.mark.asyncio()
async def test_update_payment_intent(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )
    await repo.create(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_999999",
        amount=1481850,
        currency="JPY",
        version=0,
    )
    await repo.update(payment_intent)

    db_payment_intent = await repo.get(payment_intent.id)
    assert db_payment_intent
    assert db_payment_intent.id == "pi_123456"
    assert db_payment_intent.state == PaymentIntentState.CHARGED
    assert db_payment_intent.customer_id == "cust_123456"
    assert db_payment_intent.amount == 1481850
    assert db_payment_intent.currency == "USD"
    assert db_payment_intent.version == 1


@pytest.mark.asyncio()
async def test_update_payment_intent_fails_on_optimistic_lock_error(repo: DynamoDBPaymentIntentRepository) -> None:
    # Arrange
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )
    await repo.create(payment_intent)

    # Act
    await repo.update(payment_intent)  # Increments version in DynamoDB

    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CHARGE_FAILED,
        customer_id="cust_123456",
        amount=2963700,
        currency="USD",
        version=0,  # Attempt to update the item with old version
    )
    with pytest.raises(OptimisticLockError, match=payment_intent.id):
        await repo.update(payment_intent)

    # Assert
    db_payment_intent = await repo.get(payment_intent.id)
    assert db_payment_intent
    assert db_payment_intent.state == PaymentIntentState.CREATED  # Not updated
    assert db_payment_intent.amount == 100  # Not updated
    assert db_payment_intent.version == 1


@pytest.mark.asyncio()
async def test_should_raise_on_not_existing_payment_intent_update(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )

    with pytest.raises(PaymentIntentNotFoundError, match=payment_intent.id):
        await repo.update(payment_intent)

    assert await repo.get("123456") is None
