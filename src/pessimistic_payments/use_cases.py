from .domain import PaymentIntent, PaymentIntentNotFoundError
from .payment_gateway import PaymentGateway
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


async def charge_payment_intent(
    payment_intent_id: str, repository: PaymentIntentRepository, payment_gateway: PaymentGateway
) -> PaymentIntent:
    payment_intent = await repository.get(payment_intent_id)
    if not payment_intent:
        raise PaymentIntentNotFoundError(payment_intent_id)

    async with repository.lock(payment_intent):
        await payment_intent.charge(payment_gateway)
        await repository.update(payment_intent)

    return payment_intent
