from typing import AsyncGenerator

import pytest
import pytest_asyncio
from types_aiobotocore_dynamodb import DynamoDBClient

from adapters.dynamodb import create_table
from pessimistic_payments.repository import DynamoDBPaymentIntentRepository


@pytest.fixture()
def dynamodb_table_name() -> str:
    return "autotest-pessimistic-payments"


@pytest_asyncio.fixture()
async def repo(
    localstack_dynamodb_client: DynamoDBClient, dynamodb_table_name: str
) -> AsyncGenerator[DynamoDBPaymentIntentRepository, None]:
    await create_table(localstack_dynamodb_client, dynamodb_table_name)
    yield DynamoDBPaymentIntentRepository(localstack_dynamodb_client, dynamodb_table_name)
    await localstack_dynamodb_client.delete_table(TableName=dynamodb_table_name)
