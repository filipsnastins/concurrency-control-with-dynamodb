import json

import pytest
from botocore.exceptions import ClientError

from optimistic_payments.domain import Charge, PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState
from optimistic_payments.events import PaymentIntentChargeRequested
from optimistic_payments.repository import DynamoDBPaymentIntentRepository, OptimisticLockError
from optimistic_payments.repository.dynamodb import PaymentIntentEventDTO


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
        events=[],
        version=0,
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
        events=[],
        version=0,
    )

    await repo.create(payment_intent)

    with pytest.raises(ClientError):
        await repo.create(payment_intent)


@pytest.mark.asyncio()
async def test_should_raise_on_not_existing_payment_intent_update_and_not_create_item(
    repo: DynamoDBPaymentIntentRepository,
) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[],
        version=0,
    )

    with pytest.raises(OptimisticLockError, match=payment_intent.id):
        await repo.update(payment_intent)

    with pytest.raises(PaymentIntentNotFoundError, match=payment_intent.id):
        await repo.get(payment_intent.id)


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
        events=[],
        version=0,
    )
    await repo.create(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_999999",
        amount=1481850,
        currency="JPY",
        charge=charge,
        events=[],
        version=0,
    )
    await repo.update(payment_intent)

    assert await repo.get(payment_intent.id) == PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CHARGED,
        customer_id="cust_123456",
        amount=1481850,
        currency="USD",
        charge=charge,
        events=[],
        version=1,
    )


@pytest.mark.asyncio()
async def test_optimistic_lock_handles_concurrent_payment_intent_updates(repo: DynamoDBPaymentIntentRepository) -> None:
    # Arrange
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[],
        version=0,
    )
    await repo.create(payment_intent)

    # Act
    await repo.update(payment_intent)  # Increments version in DynamoDB

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_999999",
        amount=1481850,
        currency="JPY",
        charge=None,
        events=[],
        version=0,
    )
    with pytest.raises(OptimisticLockError, match=payment_intent.id):
        await repo.update(payment_intent)

    # Assert
    assert await repo.get(payment_intent.id) == PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,  # Not updated
        customer_id="cust_123456",
        amount=100,  # Not updated
        currency="USD",
        charge=None,
        events=[],
        version=1,  # Updated by the first update
    )


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent_event(repo: DynamoDBPaymentIntentRepository) -> None:
    assert await repo.get_event("pi_123456", "evt_123456") is None


@pytest.mark.asyncio()
async def test_publish_payment_intent_events(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[],
        version=0,
    )
    await repo.create(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[
            PaymentIntentChargeRequested(
                id="evt_123456",
                payment_intent_id="pi_123456",
                amount=100,
                currency="USD",
            ),
            PaymentIntentChargeRequested(
                id="evt_999999",
                payment_intent_id="pi_123456",
                amount=100,
                currency="USD",
            ),
        ],
        version=0,
    )
    await repo.update(payment_intent)

    assert await repo.get_event(payment_intent.id, "evt_123456") == PaymentIntentEventDTO(
        PK="PAYMENT_INTENT#pi_123456",
        SK="EVENT#evt_123456",
        Id="evt_123456",
        Name="PaymentIntentChargeRequested",
        AggregateId="pi_123456",
        AggregateName="PaymentIntent",
        Payload=json.dumps(
            {
                "id": "evt_123456",
                "name": "PaymentIntentChargeRequested",
                "payment_intent_id": "pi_123456",
                "amount": 100,
                "currency": "USD",
            }
        ),
    )
    assert await repo.get_event(payment_intent.id, "evt_999999") == PaymentIntentEventDTO(
        PK="PAYMENT_INTENT#pi_123456",
        SK="EVENT#evt_999999",
        Id="evt_999999",
        Name="PaymentIntentChargeRequested",
        AggregateId="pi_123456",
        AggregateName="PaymentIntent",
        Payload=json.dumps(
            {
                "id": "evt_999999",
                "name": "PaymentIntentChargeRequested",
                "payment_intent_id": "pi_123456",
                "amount": 100,
                "currency": "USD",
            }
        ),
    )


@pytest.mark.asyncio()
async def test_should_raise_on_already_existing_event_id(repo: DynamoDBPaymentIntentRepository) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[],
        version=0,
    )
    await repo.create(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[
            PaymentIntentChargeRequested(
                id="evt_123456",
                payment_intent_id="pi_123456",
                amount=100,
                currency="USD",
            )
        ],
        version=0,
    )
    await repo.update(payment_intent)

    payment_intent = PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CHARGED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        charge=None,
        events=[
            PaymentIntentChargeRequested(
                id="evt_123456",
                payment_intent_id="pi_123456",
                amount=100,
                currency="USD",
            )
        ],
        version=1,
    )

    with pytest.raises(ClientError):
        await repo.update(payment_intent)
