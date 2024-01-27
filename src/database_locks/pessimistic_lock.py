import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Mapping

from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_dynamodb.type_defs import UniversalAttributeValueTypeDef

from . import time


class PessimisticLockAcquisitionError(Exception):
    pass


class PessimisticLockItemNotFoundError(Exception):
    pass


class DynamoDBPessimisticLock:
    def __init__(
        self,
        client: DynamoDBClient,
        table_name: str,
        *,
        lock_timeout: datetime.timedelta | None = None,
        lock_attribute: str = "__LockedAt",
    ) -> None:
        self._client = client
        self._table_name = table_name
        self._lock_timeout = lock_timeout
        self._lock_attribute = lock_attribute

    @asynccontextmanager
    async def __call__(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> AsyncGenerator[None, None]:
        lock_acquired = False
        try:
            await self._acquire_lock(key)
            lock_acquired = True
            yield
        finally:
            if lock_acquired:
                await self._release_lock(key)

    async def _acquire_lock(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key=key,
                UpdateExpression="SET #LockAttribute = :LockAttribute",
                ExpressionAttributeNames={"#LockAttribute": self._lock_attribute},
                ExpressionAttributeValues={
                    ":LockAttribute": {"S": time.now().isoformat()},
                    **self._lock_timeout_attribute_value(),
                },
                ConditionExpression=f"{self._item_exists_expression(key)} AND {self._lock_not_acquired_expression()}",
            )
        except self._client.exceptions.ConditionalCheckFailedException as e:
            raise PessimisticLockAcquisitionError(key) from e

    async def _release_lock(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> None:
        try:
            await self._client.update_item(
                TableName=self._table_name,
                Key=key,
                UpdateExpression="REMOVE #LockAttribute",
                ExpressionAttributeNames={"#LockAttribute": self._lock_attribute},
                ConditionExpression=self._item_exists_expression(key),
            )
        except self._client.exceptions.ConditionalCheckFailedException as e:
            raise PessimisticLockItemNotFoundError(key) from e

    def _item_exists_expression(self, key: Mapping[str, UniversalAttributeValueTypeDef]) -> str:
        return " AND ".join(f"attribute_exists({v})" for v in key.keys()).removesuffix(" AND ")

    def _lock_timeout_attribute_value(self) -> dict:
        if not self._lock_timeout:
            return {}
        return {":LockExpiresAt": {"S": (time.now() - self._lock_timeout).isoformat()}}

    def _lock_not_acquired_expression(self) -> str:
        if not self._lock_timeout:
            return "attribute_not_exists(#LockAttribute)"
        return "(attribute_not_exists(#LockAttribute) OR :LockExpiresAt > #LockAttribute)"
