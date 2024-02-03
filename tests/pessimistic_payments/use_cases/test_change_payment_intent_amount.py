import asyncio

import pytest
from pytest_mock import MockerFixture

from pessimistic_payments.domain import PaymentIntentNotFoundError
from pessimistic_payments.repository import PaymentIntentRepository
from pessimistic_payments.use_cases import change_payment_intent_amount, create_payment_intent, get_payment_intent


@pytest.mark.asyncio()
async def test_change_not_existing_payment_intent_amount(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError):
        await change_payment_intent_amount("pi_123456", 200, repo)


@pytest.mark.asyncio()
async def test_change_created_payment_intent_amount(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    await change_payment_intent_amount(payment_intent.id, 200, repo)

    assert (await get_payment_intent(payment_intent.id, repo)).amount == 200


@pytest.mark.asyncio()
async def test_payment_intent_amount_changed_once(repo: PaymentIntentRepository, mocker: MockerFixture) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    repo_update_spy = mocker.spy(repo, "update")

    await asyncio.wait(
        [
            asyncio.create_task(change_payment_intent_amount(payment_intent.id, 200, repo)),
            asyncio.create_task(change_payment_intent_amount(payment_intent.id, 300, repo)),
        ]
    )

    repo_update_spy.assert_awaited_once()
