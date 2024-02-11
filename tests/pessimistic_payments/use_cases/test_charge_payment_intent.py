import asyncio
from unittest.mock import Mock

import pytest

from database_locks.pessimistic_lock import PessimisticLockAcquisitionError
from pessimistic_payments.domain import Charge, PaymentIntentStateError
from pessimistic_payments.payment_gateway import PaymentGateway, PaymentGatewayResponse
from pessimistic_payments.repository import PaymentIntentRepository
from pessimistic_payments.use_cases import charge_payment_intent, create_payment_intent, get_payment_intent


@pytest.mark.asyncio()
async def test_charge_not_existing_payment_intent(repo: PaymentIntentRepository) -> None:
    payment_gw_mock = Mock(spec_set=PaymentGateway)

    with pytest.raises(PessimisticLockAcquisitionError):
        await charge_payment_intent("pi_123456", repo, payment_gw_mock)

    payment_gw_mock.charge.assert_not_called()


@pytest.mark.asyncio()
async def test_payment_intent_charged(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)
    payment_gw_mock.charge.return_value = PaymentGatewayResponse(id="ch_123456")

    await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    payment_gw_mock.charge.assert_awaited_once_with(payment_intent.id, payment_intent.amount, payment_intent.currency)
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == "CHARGED"
    assert payment_intent.charge == Charge(
        id="ch_123456",
        error_code=None,
        error_message=None,
    )


@pytest.mark.asyncio()
async def test_payment_intent_charge_failed(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)
    payment_gw_mock.charge.return_value = PaymentGatewayResponse(
        id="ch_123456",
        error_code="card_declined",
        error_message="Your card was declined.",
    )

    await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    payment_gw_mock.charge.assert_awaited_once_with(payment_intent.id, payment_intent.amount, payment_intent.currency)
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == "CHARGE_FAILED"
    assert payment_intent.charge == Charge(
        id="ch_123456",
        error_code="card_declined",
        error_message="Your card was declined.",
    )


@pytest.mark.asyncio()
async def test_charged_payment_intent_cannot_be_charged_again(repo: PaymentIntentRepository) -> None:
    # Arrange
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)
    payment_gw_mock.charge.return_value = PaymentGatewayResponse(id="ch_123456")

    # Act
    await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)
    payment_gw_mock.reset_mock()

    with pytest.raises(PaymentIntentStateError, match="PaymentIntent is not in a chargeable state: CHARGED"):
        await charge_payment_intent(payment_intent.id, repo, payment_gw_mock)

    # Assert
    payment_gw_mock.charge.assert_not_called()


@pytest.mark.asyncio()
async def test_payment_intent_charged_once(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    payment_gw_mock = Mock(spec_set=PaymentGateway)
    payment_gw_mock.charge.return_value = PaymentGatewayResponse(id="ch_123456")

    await asyncio.wait(
        [
            asyncio.create_task(charge_payment_intent(payment_intent.id, repo, payment_gw_mock)),
            asyncio.create_task(charge_payment_intent(payment_intent.id, repo, payment_gw_mock)),
        ]
    )

    payment_gw_mock.charge.assert_awaited_once()
