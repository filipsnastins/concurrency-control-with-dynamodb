from unittest import mock

import pytest

from optimistic_payments.domain import PaymentIntentNotFoundError, PaymentIntentState, PaymentIntentStateError
from optimistic_payments.events import PaymentIntentChargeRequested
from optimistic_payments.repository import PaymentIntentRepository
from optimistic_payments.use_cases import create_payment_intent, get_payment_intent, request_payment_request_charge


@pytest.mark.asyncio()
async def test_request_not_existing_payment_request_charge(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await request_payment_request_charge("pi_123456", repo)


@pytest.mark.asyncio()
async def test_request_payment_request_charge(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    payment_intent = await request_payment_request_charge(payment_intent.id, repo)

    assert payment_intent.state == PaymentIntentState.CHARGE_REQUESTED
    assert payment_intent.events == [
        PaymentIntentChargeRequested(
            id=mock.ANY,
            name="PaymentIntentChargeRequested",
            payment_intent_id=payment_intent.id,
            amount=100,
            currency="USD",
        )
    ]
    assert (await get_payment_intent(payment_intent.id, repo)).state == PaymentIntentState.CHARGE_REQUESTED


@pytest.mark.asyncio()
async def test_charge_requested_payment_intent_cannot_be_charged_again(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    await request_payment_request_charge(payment_intent.id, repo)

    with pytest.raises(PaymentIntentStateError, match="Cannot charge PaymentIntent in state: CHARGE_REQUESTED"):
        await request_payment_request_charge(payment_intent.id, repo)
