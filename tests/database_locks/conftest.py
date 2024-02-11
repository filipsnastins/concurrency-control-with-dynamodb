import uuid
from typing import AsyncGenerator

import pytest_asyncio
from types_aiobotocore_dynamodb import DynamoDBClient

from adapters.dynamodb import create_table
from database_locks import DynamoDBPessimisticLock


@pytest_asyncio.fixture()
async def dynamodb_table_name(localstack_dynamodb_client: DynamoDBClient) -> AsyncGenerator[str, None]:
    table_name = f"autotest-dynamodb-pessimistic-lock-{uuid.uuid4()}"
    await create_table(localstack_dynamodb_client, table_name, with_range_key=True)
    yield table_name
    await localstack_dynamodb_client.delete_table(TableName=table_name)


@pytest_asyncio.fixture()
async def dynamodb_pessimistic_lock(
    localstack_dynamodb_client: DynamoDBClient, dynamodb_table_name: str
) -> DynamoDBPessimisticLock:
    return DynamoDBPessimisticLock(localstack_dynamodb_client, dynamodb_table_name)
