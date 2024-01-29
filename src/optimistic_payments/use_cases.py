from .domain import PaymentIntent
from .repository import PaymentIntentRepository


async def get_payment_intent(payment_intent_id: str, repository: PaymentIntentRepository) -> PaymentIntent:
    return await repository.get(payment_intent_id)


async def create_payment_intent(
    customer_id: str, amount: int, currency: str, repository: PaymentIntentRepository
) -> PaymentIntent:
    payment_intent = PaymentIntent.create(customer_id, amount, currency)
    await repository.create(payment_intent)
    return payment_intent


async def change_payment_intent_amount(
    payment_intent_id: str, amount: int, repository: PaymentIntentRepository
) -> PaymentIntent:
    payment_intent = await repository.get(payment_intent_id)

    payment_intent.change_amount(amount)
    await repository.update(payment_intent)

    return payment_intent


async def request_payment_request_charge(payment_intent_id: str, repository: PaymentIntentRepository) -> PaymentIntent:
    payment_intent = await repository.get(payment_intent_id)

    payment_intent.request_charge()
    await repository.update(payment_intent)

    return payment_intent


async def handle_payment_intent_charge_response(
    payment_intent_id: str,
    charge_id: str,
    error_code: str | None,
    error_message: str | None,
    repository: PaymentIntentRepository,
) -> PaymentIntent:
    payment_intent = await repository.get(payment_intent_id)

    payment_intent.handle_charge_response(charge_id, error_code, error_message)
    await repository.update(payment_intent)

    return payment_intent
