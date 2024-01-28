import json
from typing import Protocol

import boto3.dynamodb.types
from pydantic import BaseModel
from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_dynamodb.type_defs import (
    AttributeValueTypeDef,
    TransactWriteItemTypeDef,
    UniversalAttributeValueTypeDef,
)

from database_locks import DynamoDBPessimisticLock

from .domain import PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState
from .events import PaymentIntentEvent

BOTO3_DESERIALIZER = boto3.dynamodb.types.TypeDeserializer()
BOTO3_SERIALIZER = boto3.dynamodb.types.TypeSerializer()


class PaymentIntentRepository(Protocol):
    async def get(self, payment_intent_id: str) -> PaymentIntent | None:
        ...  # pragma: no cover

    async def create(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover

    async def update(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover


class OptimisticLockError(Exception):
    pass


class PaymentIntentDTO(BaseModel):
    PK: str
    SK: str
    Id: str
    State: PaymentIntentState
    CustomerId: str
    Amount: int
    Currency: str
    Version: int
    Events: list[PaymentIntentEvent]

    @staticmethod
    def key(payment_intent_id: str) -> dict[str, UniversalAttributeValueTypeDef]:
        return {
            "PK": {"S": f"PAYMENT_INTENT#{payment_intent_id}"},
            "SK": {"S": "PAYMENT_INTENT"},
        }

    @staticmethod
    def create(payment_intent: PaymentIntent) -> "PaymentIntentDTO":
        return PaymentIntentDTO(
            PK=f"PAYMENT_INTENT#{payment_intent.id}",
            SK="PAYMENT_INTENT",
            Id=payment_intent.id,
            State=payment_intent.state,
            CustomerId=payment_intent.customer_id,
            Amount=payment_intent.amount,
            Currency=payment_intent.currency,
            Events=payment_intent.events,
            Version=payment_intent.version,
        )

    @staticmethod
    def from_item(item: dict[str, AttributeValueTypeDef]) -> "PaymentIntent":
        dto = PaymentIntentDTO(**{k: BOTO3_DESERIALIZER.deserialize(v) for k, v in item.items()})
        return PaymentIntent(
            id=dto.Id,
            state=dto.State,
            customer_id=dto.CustomerId,
            amount=dto.Amount,
            currency=dto.Currency,
            version=dto.Version,
            events=[],
        )

    def create_item_request(self) -> dict[str, AttributeValueTypeDef]:
        return {k: BOTO3_SERIALIZER.serialize(v) for k, v in self.model_dump().items()}

    def update_item_request(self, table_name: str) -> TransactWriteItemTypeDef:
        return {
            "Update": {
                "TableName": table_name,
                "Key": {
                    "PK": {"S": self.PK},
                    "SK": {"S": self.SK},
                },
                "UpdateExpression": "SET #State = :State, #Amount = :Amount, #Version = :Version",
                "ExpressionAttributeNames": {
                    "#State": "State",
                    "#Amount": "Amount",
                    "#Version": "Version",
                },
                "ExpressionAttributeValues": {
                    ":State": {"S": self.State},
                    ":Amount": {"N": str(self.Amount)},
                    ":Version": {"N": str(self.Version + 1)},
                },
                "ConditionExpression": "attribute_exists(Id)",
            }
        }

    def optimistic_lock_request(self, table_name: str) -> TransactWriteItemTypeDef:
        return {
            "Put": {
                "TableName": table_name,
                "Item": {
                    "PK": {"S": self.PK},
                    "SK": {"S": "OPTIMISTIC_LOCK"},
                    "Version": {"N": str(self.Version + 1)},
                },
                "ExpressionAttributeValues": {
                    ":Version": {"N": str(self.Version)},
                },
                "ConditionExpression": "attribute_not_exists(Version) OR Version = :Version",
            }
        }

    def add_event_requests(self, table_name: str) -> list[TransactWriteItemTypeDef]:
        return [PaymentIntentEventDTO.create(event).create_item_request(table_name) for event in self.Events]


class PaymentIntentEventDTO(BaseModel):
    PK: str
    SK: str
    Id: str
    Name: str
    AggregateId: str
    AggregateName: str
    Payload: str

    @staticmethod
    def key(event_id: str) -> dict[str, UniversalAttributeValueTypeDef]:
        return {
            "PK": {"S": f"EVENT#{event_id}"},
            "SK": {"S": "EVENT"},
        }

    @staticmethod
    def create(event: PaymentIntentEvent) -> "PaymentIntentEventDTO":
        return PaymentIntentEventDTO(
            PK=f"EVENT#{event.id}",
            SK="EVENT",
            Id=event.id,
            Name=event.name,
            AggregateId=event.payment_intent_id,
            AggregateName="PaymentIntent",
            Payload=json.dumps(event.to_dict()),
        )

    @staticmethod
    def from_item(item: dict[str, AttributeValueTypeDef]) -> "PaymentIntentEventDTO":
        return PaymentIntentEventDTO(**{k: BOTO3_DESERIALIZER.deserialize(v) for k, v in item.items()})

    def create_item_request(self, table_name: str) -> TransactWriteItemTypeDef:
        return {
            "Put": {
                "TableName": table_name,
                "Item": {k: BOTO3_SERIALIZER.serialize(v) for k, v in self.model_dump().items()},
                "ConditionExpression": "attribute_not_exists(Id)",
            }
        }


class DynamoDBPaymentIntentRepository:
    def __init__(self, client: DynamoDBClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._lock = DynamoDBPessimisticLock(self._client, self._table_name)

    async def get(self, payment_intent_id: str) -> PaymentIntent | None:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key=PaymentIntentDTO.key(payment_intent_id),
            ConsistentRead=True,
        )
        item = response.get("Item")
        if item is None:
            return None
        return PaymentIntentDTO.from_item(item)

    async def create(self, payment_intent: PaymentIntent) -> None:
        payment_intent_dto = PaymentIntentDTO.create(payment_intent)
        await self._client.put_item(
            TableName=self._table_name,
            Item=payment_intent_dto.create_item_request(),
            ConditionExpression="attribute_not_exists(Id)",
        )

    async def update(self, payment_intent: PaymentIntent) -> None:
        try:
            payment_intent_dto = PaymentIntentDTO.create(payment_intent)
            await self._client.transact_write_items(
                TransactItems=[
                    payment_intent_dto.update_item_request(self._table_name),
                    payment_intent_dto.optimistic_lock_request(self._table_name),
                    *payment_intent_dto.add_event_requests(self._table_name),
                ]
            )
        except self._client.exceptions.TransactionCanceledException as e:
            cancellation_reasons = e.response["CancellationReasons"]
            if cancellation_reasons[0]["Code"] == "ConditionalCheckFailed":
                raise PaymentIntentNotFoundError(payment_intent.id) from e
            if cancellation_reasons[1]["Code"] == "ConditionalCheckFailed":
                raise OptimisticLockError(payment_intent.id) from e
            raise

    async def get_event(self, event_id: str) -> PaymentIntentEventDTO | None:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key=PaymentIntentEventDTO.key(event_id),
        )
        item = response.get("Item")
        if item is None:
            return None
        return PaymentIntentEventDTO.from_item(item)
