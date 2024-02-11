from unittest import mock

import pytest

from optimistic_payments.domain import Charge, PaymentIntentNotFoundError, PaymentIntentState, PaymentIntentStateError
from optimistic_payments.events import PaymentIntentChargeRequested
from optimistic_payments.repository import PaymentIntentRepository
from optimistic_payments.use_cases import (
    create_payment_intent,
    get_payment_intent,
    handle_payment_intent_charge_response,
    request_payment_request_charge,
)


@pytest.mark.asyncio()
async def test_request_not_existing_payment_request_charge(repo: PaymentIntentRepository) -> None:
    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await request_payment_request_charge("pi_123456", repo)

    with pytest.raises(PaymentIntentNotFoundError, match="pi_123456"):
        await handle_payment_intent_charge_response("pi_123456", "ch_123456", None, None, repo)


@pytest.mark.asyncio()
async def test_requested_payment_intent_charge_succeeded(repo: PaymentIntentRepository) -> None:
    # Arrange
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    # Act
    payment_intent = await request_payment_request_charge(payment_intent.id, repo)

    # Assert
    assert payment_intent.events == [
        PaymentIntentChargeRequested(
            id=mock.ANY,
            name="PaymentIntentChargeRequested",
            payment_intent_id=payment_intent.id,
            amount=100,
            currency="USD",
        )
    ]
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == PaymentIntentState.CHARGE_REQUESTED
    assert payment_intent.charge is None

    # Act
    await handle_payment_intent_charge_response(payment_intent.id, "ch_123456", None, None, repo)

    # Assert
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == PaymentIntentState.CHARGED
    assert payment_intent.charge == Charge(id="ch_123456", error_code=None, error_message=None)


@pytest.mark.asyncio()
async def test_requested_payment_intent_charge_failed(repo: PaymentIntentRepository) -> None:
    # Arrange
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    # Act
    payment_intent = await request_payment_request_charge(payment_intent.id, repo)

    # Assert
    assert payment_intent.events == [
        PaymentIntentChargeRequested(
            id=mock.ANY,
            name="PaymentIntentChargeRequested",
            payment_intent_id=payment_intent.id,
            amount=100,
            currency="USD",
        )
    ]
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == PaymentIntentState.CHARGE_REQUESTED
    assert payment_intent.charge is None

    # Act
    await handle_payment_intent_charge_response(
        payment_intent.id,
        "ch_123456",
        "card_declined",
        "Your card was declined.",
        repo,
    )

    # Assert
    payment_intent = await get_payment_intent(payment_intent.id, repo)
    assert payment_intent.state == PaymentIntentState.CHARGE_FAILED
    assert payment_intent.charge == Charge(
        id="ch_123456",
        error_code="card_declined",
        error_message="Your card was declined.",
    )


@pytest.mark.asyncio()
async def test_charge_requested_payment_intent_cannot_be_charged_again(repo: PaymentIntentRepository) -> None:
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)

    await request_payment_request_charge(payment_intent.id, repo)

    with pytest.raises(PaymentIntentStateError, match="Cannot charge PaymentIntent in state: CHARGE_REQUESTED"):
        await request_payment_request_charge(payment_intent.id, repo)


@pytest.mark.asyncio()
async def test_charged_payment_intent_cannot_be_charged_again(repo: PaymentIntentRepository) -> None:
    # Arrange
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    await request_payment_request_charge(payment_intent.id, repo)
    await handle_payment_intent_charge_response(payment_intent.id, "ch_123456", None, None, repo)

    # Act & Assert
    with pytest.raises(PaymentIntentStateError, match="Cannot charge PaymentIntent in state: CHARGED"):
        await request_payment_request_charge(payment_intent.id, repo)

    # Act & Assert
    with pytest.raises(
        PaymentIntentStateError, match="Cannot handle charge response when PaymentIntent in state: CHARGED"
    ):
        await handle_payment_intent_charge_response(payment_intent.id, "ch_999999", None, None, repo)

    # Assert
    assert (await get_payment_intent(payment_intent.id, repo)).charge == Charge(
        id="ch_123456",
        error_code=None,
        error_message=None,
    )


@pytest.mark.asyncio()
async def test_charge_failed_payment_intent_cannot_be_charged_again(repo: PaymentIntentRepository) -> None:
    # Arrange
    payment_intent = await create_payment_intent("cust_123456", 100, "USD", repo)
    await request_payment_request_charge(payment_intent.id, repo)
    await handle_payment_intent_charge_response(payment_intent.id, "ch_123456", "card_declined", None, repo)

    # Act & Assert
    with pytest.raises(PaymentIntentStateError, match="Cannot charge PaymentIntent in state: CHARGE_FAILED"):
        await request_payment_request_charge(payment_intent.id, repo)

    # Act & Assert
    with pytest.raises(
        PaymentIntentStateError, match="Cannot handle charge response when PaymentIntent in state: CHARGE_FAILED"
    ):
        await handle_payment_intent_charge_response(payment_intent.id, "ch_999999", None, None, repo)

    # Assert
    assert (await get_payment_intent(payment_intent.id, repo)).charge == Charge(
        id="ch_123456",
        error_code="card_declined",
        error_message=None,
    )
