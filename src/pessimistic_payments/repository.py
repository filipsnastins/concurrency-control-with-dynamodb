import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Protocol

from types_aiobotocore_dynamodb import DynamoDBClient

from .domain import PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState


class PaymentIntentRepository(Protocol):
    @asynccontextmanager
    async def lock(self, payment_intent: PaymentIntent) -> AsyncGenerator[None, None]:
        yield None

    async def get(self, id: str) -> PaymentIntent | None:
        ...

    async def create(self, payment_intent: PaymentIntent) -> None:
        ...

    async def update(self, payment_intent: PaymentIntent) -> None:
        ...


class PessimisticLockError(Exception):
    pass


class PaymentIntentIdentifierCollisionError(Exception):
    pass


class DynamoDBPaymentIntentRepository:
    def __init__(self, client: DynamoDBClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name

    @asynccontextmanager
    async def lock(self, payment_intent: PaymentIntent) -> AsyncGenerator[None, None]:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key={
                    "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                    "SK": {"S": "PAYMENT_INTENT"},
                },
                UpdateExpression="SET #LockedAt = :LockedAt",
                ExpressionAttributeNames={"#LockedAt": "__LockedAt"},
                ExpressionAttributeValues={":LockedAt": {"S": datetime.datetime.now(tz=datetime.UTC).isoformat()}},
                ConditionExpression="attribute_exists(Id) AND attribute_not_exists(#LockedAt)",
            )
        except self._client.exceptions.ConditionalCheckFailedException:
            raise PessimisticLockError(f"Unable to acquire pessimistic lock for PaymentIntent: {payment_intent.id}")
        yield
        await self._client.update_item(
            TableName=self._table_name,
            Key={
                "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                "SK": {"S": "PAYMENT_INTENT"},
            },
            UpdateExpression="REMOVE #LockedAt",
            ExpressionAttributeNames={"#LockedAt": "__LockedAt"},
            ConditionExpression="attribute_exists(Id)",
        )

    async def get(self, id: str) -> PaymentIntent | None:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key={
                "PK": {"S": f"PAYMENT_INTENT#{id}"},
                "SK": {"S": "PAYMENT_INTENT"},
            },
        )
        item = response.get("Item")
        if item is None:
            return None
        return PaymentIntent(
            id=item["Id"]["S"],
            state=PaymentIntentState(item["State"]["S"]),
            customer_id=item["CustomerId"]["S"],
            amount=int(item["Amount"]["N"]),
            currency=item["Currency"]["S"],
        )

    async def create(self, payment_intent: PaymentIntent) -> None:
        try:
            await self._client.put_item(
                TableName=self._table_name,
                Item={
                    "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                    "SK": {"S": "PAYMENT_INTENT"},
                    "Id": {"S": payment_intent.id},
                    "State": {"S": payment_intent.state},
                    "CustomerId": {"S": payment_intent.customer_id},
                    "Amount": {"N": str(payment_intent.amount)},
                    "Currency": {"S": payment_intent.currency},
                },
                ConditionExpression="attribute_not_exists(Id)",
            )
        except self._client.exceptions.ConditionalCheckFailedException:
            raise PaymentIntentIdentifierCollisionError(payment_intent.id)

    async def update(self, payment_intent: PaymentIntent) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key={
                    "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                    "SK": {"S": "PAYMENT_INTENT"},
                },
                UpdateExpression="SET #State = :State",
                ExpressionAttributeNames={"#State": "State"},
                ExpressionAttributeValues={":State": {"S": payment_intent.state}},
                ConditionExpression="attribute_exists(Id)",
            )
        except self._client.exceptions.ConditionalCheckFailedException:
            raise PaymentIntentNotFoundError(payment_intent.id)
