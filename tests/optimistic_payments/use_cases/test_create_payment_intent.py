import pytest

from optimistic_payments.domain import PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState
from optimistic_payments.repository import PaymentIntentRepository
from optimistic_payments.use_cases import create_payment_intent, get_payment_intent


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await get_payment_intent("pi_123456", repo)


@pytest.mark.asyncio()
async def test_create_payment_intent(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    assert await get_payment_intent(payment_intent.id, repo) == PaymentIntent(
        id=payment_intent.id,
        state=PaymentIntentState.CREATED,
        customer_id="cust_123456",
        amount=100,
        currency="USD",
        events=[],
        version=0,
    )
