import json
from typing import Self

from types_aiobotocore_dynamodb.type_defs import TransactWriteItemTypeDef, UniversalAttributeValueTypeDef

from optimistic_payments.events import PaymentIntentEvent

from .base import BaseDTO


class PaymentIntentEventDTO(BaseDTO[PaymentIntentEvent]):
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

    @classmethod
    def from_entity(cls: type[Self], event: PaymentIntentEvent) -> Self:
        return cls(
            PK=f"EVENT#{event.id}",
            SK="EVENT",
            Id=event.id,
            Name=event.name,
            AggregateId=event.payment_intent_id,
            AggregateName="PaymentIntent",
            Payload=json.dumps(event.to_dict()),
        )

    def to_entity(self) -> PaymentIntentEvent:
        raise NotImplementedError  # pragma: no cover

    def create_item_transact_request(self, table_name: str) -> TransactWriteItemTypeDef:
        return {
            "Put": {
                "TableName": table_name,
                "Item": self.to_dynamodb_item(),
                "ConditionExpression": "attribute_not_exists(Id)",
            }
        }
