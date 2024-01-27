import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Mapping

from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_dynamodb.type_defs import UniversalAttributeValueTypeDef

# TODO do not create item if not exists


class PessimisticLockError(Exception):
    pass


class DynamoDBPessimisticLock:
    def __init__(self, client: DynamoDBClient, table_name: str, lock_attribute: str = "__LockedAt") -> None:
        self._client = client
        self._table_name = table_name
        self._lock_attribute = lock_attribute

    @asynccontextmanager
    async def __call__(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> AsyncGenerator[None, None]:
        await self._acquire_lock(key)
        yield
        await self._release_lock(key)

    async def _acquire_lock(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key=key,
                UpdateExpression="SET #LockAttribute = :LockAttribute",
                ExpressionAttributeNames={"#LockAttribute": self._lock_attribute},
                ExpressionAttributeValues={":LockAttribute": {"S": self._now()}},
                ConditionExpression="attribute_not_exists(#LockAttribute)",
            )
        except self._client.exceptions.ConditionalCheckFailedException:
            raise PessimisticLockError(key)

    async def _release_lock(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> None:
        await self._client.update_item(
            TableName=self._table_name,
            Key=key,
            UpdateExpression="REMOVE #LockAttribute",
            ExpressionAttributeNames={"#LockAttribute": self._lock_attribute},
        )

    def _now(self) -> str:
        return datetime.datetime.now(tz=datetime.UTC).isoformat()
