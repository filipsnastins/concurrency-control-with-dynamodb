import json
from typing import Protocol

import boto3.dynamodb.types
from pydantic import BaseModel
from types_aiobotocore_dynamodb.type_defs import (
    AttributeValueTypeDef,
    TransactWriteItemTypeDef,
    UniversalAttributeValueTypeDef,
)

from ...domain import PaymentIntent, PaymentIntentState
from ...events import PaymentIntentEvent

BOTO3_DESERIALIZER = boto3.dynamodb.types.TypeDeserializer()
BOTO3_SERIALIZER = boto3.dynamodb.types.TypeSerializer()


class PaymentIntentRepository(Protocol):
    async def get(self, payment_intent_id: str) -> PaymentIntent | None:
        ...  # pragma: no cover

    async def create(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover

    async def update(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover


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
