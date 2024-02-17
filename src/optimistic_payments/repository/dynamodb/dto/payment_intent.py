import json
from dataclasses import asdict
from typing import Self

from types_aiobotocore_dynamodb.type_defs import TransactWriteItemTypeDef, UniversalAttributeValueTypeDef

from optimistic_payments.domain import Charge, PaymentIntent, PaymentIntentState

from .abstract import AbstractDTO
from .payment_intent_event import PaymentIntentEventDTO


class PaymentIntentDTO(AbstractDTO[PaymentIntent]):
    PK: str
    SK: str
    Id: str
    State: PaymentIntentState
    CustomerId: str
    Amount: int
    Currency: str
    Charge: str | None
    Events: list[PaymentIntentEventDTO]
    Version: int

    @staticmethod
    def key(payment_intent_id: str) -> dict[str, UniversalAttributeValueTypeDef]:
        return {
            "PK": {"S": f"PAYMENT_INTENT#{payment_intent_id}"},
            "SK": {"S": "#PAYMENT_INTENT"},
        }

    @classmethod
    def from_entity(cls: type[Self], payment_intent: PaymentIntent) -> Self:
        return cls(
            PK=f"PAYMENT_INTENT#{payment_intent.id}",
            SK="#PAYMENT_INTENT",
            Id=payment_intent.id,
            State=payment_intent.state,
            CustomerId=payment_intent.customer_id,
            Amount=payment_intent.amount,
            Currency=payment_intent.currency,
            Charge=json.dumps(asdict(payment_intent.charge)) if payment_intent.charge else None,
            Events=[PaymentIntentEventDTO.from_entity(event) for event in payment_intent.events],
            Version=payment_intent.version,
        )

    def to_entity(self) -> PaymentIntent:
        return PaymentIntent(
            id=self.Id,
            state=self.State,
            customer_id=self.CustomerId,
            amount=self.Amount,
            currency=self.Currency,
            charge=Charge(**json.loads(self.Charge)) if self.Charge else None,
            events=[],
            version=self.Version,
        )

    def update_item_request(self, table_name: str) -> TransactWriteItemTypeDef:
        return {
            "Update": {
                "TableName": table_name,
                "Key": {
                    "PK": {"S": self.PK},
                    "SK": {"S": self.SK},
                },
                "UpdateExpression": "SET #State = :State, #Amount = :Amount, #Charge = :Charge, #Version = :NewVersion",
                "ExpressionAttributeNames": {
                    "#State": "State",
                    "#Amount": "Amount",
                    "#Charge": "Charge",
                    "#Version": "Version",
                },
                "ExpressionAttributeValues": {
                    ":State": {"S": self.State},
                    ":Amount": {"N": str(self.Amount)},
                    ":Charge": {"S": self.Charge} if self.Charge else {"NULL": True},
                    ":NewVersion": {"N": str(self.Version + 1)},
                    ":CurrentVersion": {"N": str(self.Version)},
                },
                "ConditionExpression": "attribute_exists(Id) AND Version = :CurrentVersion",
            }
        }

    def add_event_item_requests(self, table_name: str) -> list[TransactWriteItemTypeDef]:
        return [event.create_item_request(table_name) for event in self.Events]
