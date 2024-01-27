import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Mapping

from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_dynamodb.type_defs import UniversalAttributeValueTypeDef


class PessimisticLockError(Exception):
    pass


class DynamoDBItemNotFoundError(Exception):
    pass


DynamoDBKeyType = Mapping[str, UniversalAttributeValueTypeDef]


class DynamoDBPessimisticLock:
    def __init__(self, client: DynamoDBClient, table_name: str, lock_attribute: str = "__LockedAt") -> None:
        self._client = client
        self._table_name = table_name
        self._lock_attribute = lock_attribute

    @asynccontextmanager
    async def __call__(self, key: DynamoDBKeyType) -> AsyncGenerator[None, None]:
        await self._acquire_lock(key)
        yield
        await self._release_lock(key)

    async def _acquire_lock(self, key: DynamoDBKeyType) -> None:
        try:
            await self._client.transact_write_items(
                TransactItems=[
                    {
                        "ConditionCheck": {
                            "TableName": self._table_name,
                            "Key": key,
                            "ConditionExpression": self._item_exists_condition_expression(key),
                        },
                    },
                    {
                        "Update": {
                            "TableName": self._table_name,
                            "Key": key,
                            "UpdateExpression": "SET #LockAttribute = :LockAttribute",
                            "ExpressionAttributeNames": {"#LockAttribute": self._lock_attribute},
                            "ExpressionAttributeValues": {":LockAttribute": {"S": self._now()}},
                            "ConditionExpression": "attribute_not_exists(#LockAttribute)",
                        }
                    },
                ]
            )
        except self._client.exceptions.TransactionCanceledException as e:
            if e.response["CancellationReasons"][0]["Code"] == "ConditionalCheckFailed":
                raise DynamoDBItemNotFoundError(key) from e
            if e.response["CancellationReasons"][1]["Code"] == "ConditionalCheckFailed":
                raise PessimisticLockError(key) from e
            raise

    async def _release_lock(self, key: DynamoDBKeyType) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key=key,
                UpdateExpression="REMOVE #LockAttribute",
                ExpressionAttributeNames={"#LockAttribute": self._lock_attribute},
                ConditionExpression=self._item_exists_condition_expression(key),
            )
        except self._client.exceptions.ConditionalCheckFailedException as e:
            raise DynamoDBItemNotFoundError(key) from e

    def _now(self) -> str:
        return datetime.datetime.now(tz=datetime.UTC).isoformat()

    def _item_exists_condition_expression(self, key: DynamoDBKeyType) -> str:
        return " AND ".join(f"attribute_exists({v})" for v in key.keys())
