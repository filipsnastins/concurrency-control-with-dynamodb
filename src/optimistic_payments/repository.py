from typing import Protocol

from types_aiobotocore_dynamodb import DynamoDBClient

from database_locks import DynamoDBPessimisticLock

from .domain import PaymentIntent, PaymentIntentNotFoundError, PaymentIntentState


class PaymentIntentRepository(Protocol):
    async def get(self, id: str) -> PaymentIntent | None:
        ...  # pragma: no cover

    async def create(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover

    async def update(self, payment_intent: PaymentIntent) -> None:
        ...  # pragma: no cover


class PaymentIntentIdentifierCollisionError(Exception):
    pass


class OptimisticLockError(Exception):
    pass


class DynamoDBPaymentIntentRepository:
    def __init__(self, client: DynamoDBClient, table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._lock = DynamoDBPessimisticLock(self._client, self._table_name)

    async def get(self, id: str) -> PaymentIntent | None:
        response = await self._client.get_item(
            TableName=self._table_name,
            Key={
                "PK": {"S": f"PAYMENT_INTENT#{id}"},
                "SK": {"S": "PAYMENT_INTENT"},
            },
            ConsistentRead=True,
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
            version=int(item["Version"]["N"]),
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
                    "Version": {"N": str(payment_intent.version)},
                },
                ConditionExpression="attribute_not_exists(Id)",
            )
        except self._client.exceptions.ConditionalCheckFailedException as e:
            raise PaymentIntentIdentifierCollisionError(payment_intent.id) from e

    async def update(self, payment_intent: PaymentIntent) -> None:
        try:
            await self._client.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self._table_name,
                            "Key": {
                                "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                                "SK": {"S": "PAYMENT_INTENT"},
                            },
                            "UpdateExpression": "SET #State = :State, #Amount = :Amount, #Version = :Version",
                            "ExpressionAttributeNames": {
                                "#State": "State",
                                "#Amount": "Amount",
                                "#Version": "Version",
                            },
                            "ExpressionAttributeValues": {
                                ":State": {"S": payment_intent.state},
                                ":Amount": {"N": str(payment_intent.amount)},
                                ":Version": {"N": str(payment_intent.version + 1)},
                            },
                            "ConditionExpression": "attribute_exists(Id)",
                        }
                    },
                    {
                        "Put": {
                            "TableName": self._table_name,
                            "Item": {
                                "PK": {"S": f"PAYMENT_INTENT#{payment_intent.id}"},
                                "SK": {"S": "OPTIMISTIC_LOCK"},
                                "Version": {"N": str(payment_intent.version + 1)},
                            },
                            "ExpressionAttributeValues": {
                                ":Version": {"N": str(payment_intent.version)},
                            },
                            "ConditionExpression": "attribute_not_exists(Version) OR Version = :Version",
                        }
                    },
                ]
            )
        except self._client.exceptions.TransactionCanceledException as e:
            if e.response["CancellationReasons"][0]["Code"] == "ConditionalCheckFailed":
                raise PaymentIntentNotFoundError(payment_intent.id) from e
            if e.response["CancellationReasons"][1]["Code"] == "ConditionalCheckFailed":
                raise OptimisticLockError(payment_intent.id) from e
            raise
