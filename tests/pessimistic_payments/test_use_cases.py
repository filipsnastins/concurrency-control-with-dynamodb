import asyncio
from unittest.mock import Mock

import pytest

from pessimistic_payments.domain import PaymentIntentNotFoundError, PaymentIntentStateError
from pessimistic_payments.payment_gateway import PaymentGateway, PaymentGatewayError, PaymentGatewayErrorResponse
from pessimistic_payments.repository import PaymentIntentRepository
from pessimistic_payments.use_cases import charge_payment_intent, create_payment_intent, get_payment_intent


@pytest.mark.asyncio()
async def test_payment_intent_charged(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("customer-123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)

    await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == "CHARGED"


@pytest.mark.asyncio()
async def test_payment_intent_charge_failed(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("customer-123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)
    payment_gw_mock.charge.side_effect = PaymentGatewayError(
        PaymentGatewayErrorResponse(
            error_code="card_declined",
            error_message="Your card was declined.",
        )
    )

    await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == "CHARGE_FAILED"


@pytest.mark.asyncio()
async def test_charged_payment_intent_cannot_be_charged_again(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("customer-123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)
    await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    with pytest.raises(PaymentIntentStateError, match="PaymentIntent is not in a chargeable state: CHARGED"):
        await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    payment_gw_mock.charge.assert_called_once_with(payment_intent.id, payment_intent.amount, payment_intent.currency)
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == "CHARGED"


@pytest.mark.asyncio()
async def test_payment_intent_charged_once(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("customer-123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)

    await asyncio.wait(
        [
            asyncio.create_task(charge_payment_intent(payment_intent.id, repo, payment_gw_mock)),
            asyncio.create_task(charge_payment_intent(payment_intent.id, repo, payment_gw_mock)),
        ]
    )

    payment_gw_mock.charge.assert_called_once_with(payment_intent.id, payment_intent.amount, payment_intent.currency)
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == "CHARGED"


@pytest.mark.asyncio()
async def test_get_not_existing_payment_intent(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi-123456"):
        await get_payment_intent("pi-123456", repo)


@pytest.mark.asyncio()
async def test_charge_not_existing_payment_intent(repo: PaymentIntentRepository) -> None:
    payment_gw_mock = Mock(spec_set=PaymentGateway)

    with pytest.raises(PaymentIntentNotFoundError, match="pi-123456"):
        await charge_payment_intent("pi-123456", repo, payment_gw_mock)

    payment_gw_mock.charge.assert_not_called()
