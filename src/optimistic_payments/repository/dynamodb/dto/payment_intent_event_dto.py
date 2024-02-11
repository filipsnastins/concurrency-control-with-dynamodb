import json
from typing import Self

from types_aiobotocore_dynamodb.type_defs import TransactWriteItemTypeDef, UniversalAttributeValueTypeDef

from optimistic_payments.events import PaymentIntentEvent

from .abstract import AbstractDTO


class PaymentIntentEventDTO(AbstractDTO[PaymentIntentEvent]):
    PK: str
    SK: str
    Id: str
    Name: str
    AggregateId: str
    AggregateName: str
    Payload: str

    @staticmethod
    def key(payment_intent_id: str, event_id: str) -> dict[str, UniversalAttributeValueTypeDef]:
        return {
            "PK": {"S": f"PAYMENT_INTENT#{payment_intent_id}"},
            "SK": {"S": f"EVENT#{event_id}"},
        }

    @classmethod
    def from_entity(cls: type[Self], event: PaymentIntentEvent) -> Self:
        return cls(
            PK=f"PAYMENT_INTENT#{event.payment_intent_id}",
            SK=f"EVENT#{event.id}",
            Id=event.id,
            Name=event.name,
            AggregateId=event.payment_intent_id,
            AggregateName="PaymentIntent",
            Payload=json.dumps(event.to_dict()),
        )

    def to_entity(self) -> PaymentIntentEvent:
        raise NotImplementedError  # pragma: no cover

    def create_item_request(self, table_name: str) -> TransactWriteItemTypeDef:
        return {
            "Put": {
                "TableName": table_name,
                "Item": self.to_dynamodb_item(),
                "ConditionExpression": "attribute_not_exists(Id)",
            }
        }
