from typing import AsyncGenerator

import pytest
import pytest_asyncio
from types_aiobotocore_dynamodb import DynamoDBClient

from adapters.dynamodb import create_table
from database_locks import DynamoDBPessimisticLock


@pytest.fixture()
def dynamodb_table_name() -> str:
    return "autotest-dynamodb-lock"


@pytest_asyncio.fixture()
async def dynamodb_pessimistic_lock(
    localstack_dynamodb_client: DynamoDBClient, dynamodb_table_name: str
) -> AsyncGenerator[DynamoDBPessimisticLock, None]:
    await create_table(localstack_dynamodb_client, dynamodb_table_name)
    yield DynamoDBPessimisticLock(localstack_dynamodb_client, dynamodb_table_name)
    await localstack_dynamodb_client.delete_table(TableName=dynamodb_table_name)
