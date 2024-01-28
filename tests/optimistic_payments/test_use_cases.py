import pytest

from optimistic_payments.domain import (
    PaymentIntent,
    PaymentIntentNotFoundError,
    PaymentIntentState,
    PaymentIntentStateError,
)
from optimistic_payments.repository import PaymentIntentRepository
from optimistic_payments.use_cases import change_payment_intent_amount, create_payment_intent, get_payment_intent


@pytest.mark.asyncio()
async def test_create_and_get_payment_intent(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    assert await get_payment_intent(payment_intent.id, repo) == PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await get_payment_intent("pi_123456", repo)


@pytest.mark.asyncio()
async def test_change_not_existing_payment_intent_amount(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await change_payment_intent_amount("pi_123456", 200, repo)


@pytest.mark.asyncio()
async def test_change_created_payment_intent_amount(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    await change_payment_intent_amount(payment_intent.id, 200, repo)

    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.amount == 200


@pytest.mark.parametrize(
    "state",
    [
        PaymentIntentState.CHARGE_REQUESTED,
        PaymentIntentState.CHARGED,
        PaymentIntentState.CHARGE_FAILED,
    ],
)
@pytest.mark.asyncio()
async def test_change_payment_intent_amount_when_payment_intent_is_not_in_created_state(
    repo: PaymentIntentRepository, state: PaymentIntentState
) -> None:
    payment_intent = PaymentIntent(
        id="pi_123456",
        state=state,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        version=0,
    )
    await repo.create(payment_intent)

    with pytest.raises(PaymentIntentStateError, match=f"Cannot change PaymentIntent amount in state: {state}"):
        await change_payment_intent_amount(payment_intent.id, 200, repo)

    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.amount == 100
