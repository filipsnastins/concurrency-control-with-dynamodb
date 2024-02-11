import pytest

from optimistic_payments.domain import PaymentIntentNotFoundError, PaymentIntentStateError
from optimistic_payments.repository import PaymentIntentRepository
from optimistic_payments.use_cases import (
    change_payment_intent_amount,
    create_payment_intent,
    get_payment_intent,
    request_payment_request_charge,
)


@pytest.mark.asyncio()
async def test_change_not_existing_payment_intent_amount(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await change_payment_intent_amount("pi_123456", 200, repo)


@pytest.mark.asyncio()
async def test_change_created_payment_intent_amount(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    await change_payment_intent_amount(payment_intent.id, 200, repo)

    assert (await get_payment_intent(payment_intent.id, repo)).amount == 200


@pytest.mark.asyncio()
async def test_cannot_change_payment_intent_amount_when_payment_intent_is_not_in_created_state(
    repo: PaymentIntentRepository,
) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    await request_payment_request_charge(payment_intent.id, repo)

    with pytest.raises(PaymentIntentStateError, match="Cannot change PaymentIntent amount in state: CHARGE_REQUESTED"):
        await change_payment_intent_amount(payment_intent.id, 200, repo)

    assert (await get_payment_intent(payment_intent.id, repo)).amount == 100
