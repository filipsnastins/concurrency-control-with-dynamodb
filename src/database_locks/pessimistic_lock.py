from contextlib import asynccontextmanager
from typing import AsyncGenerator, Mapping

from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_dynamodb.type_defs import UniversalAttributeValueTypeDef

from .time import now


class PessimisticLockError(Exception):
    pass


DynamoDBKeyType = Mapping[str, UniversalAttributeValueTypeDef]


class DynamoDBPessimisticLock:
    def __init__(self, client: DynamoDBClient, table_name: str, lock_attribute: str = "__LockedAt") -> None:
        self._client = client
        self._table_name = table_name
        self._lock_attribute = lock_attribute

    @asynccontextmanager
    async def __call__(self, key: DynamoDBKeyType) -> AsyncGenerator[None, None]:
        try:
            await self._acquire_lock(key)
            yield
        finally:
            await self._release_lock(key)

    async def _acquire_lock(self, key: DynamoDBKeyType) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key=key,
                UpdateExpression="SET #LockAttribute = :LockAttribute",
                ExpressionAttributeNames={"#LockAttribute": self._lock_attribute},
                ExpressionAttributeValues={":LockAttribute": {"S": now()}},
                ConditionExpression=f"attribute_not_exists(#LockAttribute) AND {self._item_exists_condition_expression(key)}",
            )
        except self._client.exceptions.ConditionalCheckFailedException:
            raise PessimisticLockError(key)

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
            raise PessimisticLockError(key) from e

    def _item_exists_condition_expression(self, key: DynamoDBKeyType) -> str:
        return " AND ".join(f"attribute_exists({v})" for v in key.keys())
