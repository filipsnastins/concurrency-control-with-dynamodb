import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncGenerator, Protocol

from types_aiobotocore_dynamodb import DynamoDBClient

from database_locks import DynamoDBPessimisticLock

from .domain import Charge, PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState


class PaymentIntentRepository(Protocol):
    @asynccontextmanager
    async def lock(self, payment_intent_id: str) -> AsyncGenerator[PaymentIntent, None]:
        yield  # type: ignore  # pragma: no cover

    async def get(self, payment_intent_id: str) -> PaymentIntent:
        ...  # pragma: no cover

    async def create(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover

    async def update(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover


class DynamoDBPaymentIntentRepository:
    def __init__(self, client: DynamoDBClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._lock = DynamoDBPessimisticLock(self._client, self._table_name)

    @asynccontextmanager
    async def lock(self, payment_intent_id: str) -> AsyncGenerator[PaymentIntent, None]:
        async with self._lock(
            {
                "PK": {"S": f"PAYMENT_INTENT#{payment_intent_id}"},
                "SK": {"S": "#PAYMENT_INTENT"},
            }
        ):
            yield await self.get(payment_intent_id)

    async def get(self, payment_intent_id: str) -> PaymentIntent:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key={
                "PK": {"S": f"PAYMENT_INTENT#{payment_intent_id}"},
                "SK": {"S": "#PAYMENT_INTENT"},
            },
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item is None:
            raise PaymentIntentNotFoundError(payment_intent_id)
        return PaymentIntent(
            id=item["Id"]["S"],
            state=PaymentIntentState(item["State"]["S"]),
            customer_id=item["CustomerId"]["S"],
            amount=int(item["Amount"]["N"]),
            currency=item["Currency"]["S"],
            charge=Charge(**charge_item) if (charge_item := json.loads(item["Charge"]["S"])) else None,
        )

    async def create(self, payment_intent: PaymentIntent) -> None:
        await self._client.put_item(
            TableName=self._table_name,
            Item={
                "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                "SK": {"S": "#PAYMENT_INTENT"},
                "Id": {"S": payment_intent.id},
                "State": {"S": payment_intent.state},
                "CustomerId": {"S": payment_intent.customer_id},
                "Amount": {"N": str(payment_intent.amount)},
                "Currency": {"S": payment_intent.currency},
                "Charge": {"S": json.dumps(asdict(payment_intent.charge) if payment_intent.charge else {})},
            },
            ConditionExpression="attribute_not_exists(Id)",
        )

    async def update(self, payment_intent: PaymentIntent) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key={
                    "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                    "SK": {"S": "#PAYMENT_INTENT"},
                },
                UpdateExpression="SET #State = :State, #Amount = :Amount, #Charge = :Charge",
                ExpressionAttributeNames={
                    "#State": "State",
                    "#Amount": "Amount",
                    "#Charge": "Charge",
                },
                ExpressionAttributeValues={
                    ":State": {"S": payment_intent.state},
                    ":Amount": {"N": str(payment_intent.amount)},
                    ":Charge": {"S": json.dumps(asdict(payment_intent.charge) if payment_intent.charge else {})},
                },
                ConditionExpression="attribute_exists(Id)",
            )
        except self._client.exceptions.ConditionalCheckFailedException as e:
            raise PaymentIntentNotFoundError(payment_intent.id) from e
