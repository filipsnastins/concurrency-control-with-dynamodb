from typing import AsyncGenerator

import pytest_asyncio
from types_aiobotocore_dynamodb import DynamoDBClient

from adapters.dynamodb import create_table
from pessimistic_payments.repository import DynamoDBPaymentIntentRepository


@pytest_asyncio.fixture()
async def dynamodb_table_name(
    localstack_dynamodb_client: DynamoDBClient,
) -> AsyncGenerator[str, None]:
    table_name = "autotest-pessimistic-payments"
    await create_table(localstack_dynamodb_client, table_name)
    yield table_name
    await localstack_dynamodb_client.delete_table(TableName=table_name)


@pytest_asyncio.fixture()
async def repo(localstack_dynamodb_client: DynamoDBClient, dynamodb_table_name: str) -> DynamoDBPaymentIntentRepository:
    return DynamoDBPaymentIntentRepository(localstack_dynamodb_client, dynamodb_table_name)
