from .domain import PaymentIntent, PaymentIntentNotFoundError
from .repository import PaymentIntentRepository


async def get_payment_intent(payment_intent_id: str, repository: PaymentIntentRepository) -> PaymentIntent:
    payment_intent = await repository.get(payment_intent_id)
    if not payment_intent:
        raise PaymentIntentNotFoundError(payment_intent_id)
    return payment_intent


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
    if not payment_intent:
        raise PaymentIntentNotFoundError(payment_intent_id)

    payment_intent.change_amount(amount)
    await repository.update(payment_intent)

    return payment_intent


async def request_payment_request_charge(payment_intent_id: str, repository: PaymentIntentRepository) -> PaymentIntent:
    payment_intent = await repository.get(payment_intent_id)
    if not payment_intent:
        raise PaymentIntentNotFoundError(payment_intent_id)

    payment_intent.request_charge()
    await repository.update(payment_intent)

    return payment_intent
