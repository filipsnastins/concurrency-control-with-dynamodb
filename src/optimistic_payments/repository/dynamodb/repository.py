from types_aiobotocore_dynamodb import DynamoDBClient

from optimistic_payments.domain import PaymentIntent, PaymentIntentNotFoundError

from ..exceptions import OptimisticLockError
from .dto import PaymentIntentDTO, PaymentIntentEventDTO


class DynamoDBPaymentIntentRepository:
    def __init__(self, client: DynamoDBClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    async def get(self, payment_intent_id: str) -> PaymentIntent:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key=PaymentIntentDTO.key(payment_intent_id),
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item is None:
            raise PaymentIntentNotFoundError(payment_intent_id)
        return PaymentIntentDTO.from_dynamodb_item(item).to_entity()

    async def create(self, payment_intent: PaymentIntent) -> None:
        await self._client.put_item(
            TableName=self._table_name,
            Item=PaymentIntentDTO.from_entity(payment_intent).to_dynamodb_item(),
            ConditionExpression="attribute_not_exists(Id)",
        )

    async def update(self, payment_intent: PaymentIntent) -> None:
        payment_intent_dto = PaymentIntentDTO.from_entity(payment_intent)
        try:
            await self._client.transact_write_items(
                TransactItems=[
                    payment_intent_dto.update_item_request(self._table_name),
                    *payment_intent_dto.add_event_item_requests(self._table_name),
                ]
            )
        except self._client.exceptions.TransactionCanceledException as e:
            if e.response["CancellationReasons"][0]["Code"] == "ConditionalCheckFailed":
                raise OptimisticLockError(payment_intent.id) from e
            raise

    async def get_event(self, payment_intent_id: str, event_id: str) -> PaymentIntentEventDTO | None:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key=PaymentIntentEventDTO.key(payment_intent_id, event_id),
        )
        item = response.get("Item")
        if item is None:
            return None
        return PaymentIntentEventDTO.from_dynamodb_item(item)
