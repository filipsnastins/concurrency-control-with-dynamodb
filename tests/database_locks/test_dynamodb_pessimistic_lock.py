import uuid

import pytest
from types_aiobotocore_dynamodb import DynamoDBClient

from database_locks import DynamoDBPessimisticLock
from database_locks.pessimistic_lock import DynamoDBItemNotFoundError


def generate_key() -> dict:
    return {"PK": {"S": f"ITEM#{uuid.uuid4()}"}, "SK": {"S": "ITEM"}}


@pytest.mark.asyncio()
async def test_should_not_lock_and_create_not_existing_item(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_key()

    with pytest.raises(DynamoDBItemNotFoundError, match=str(key)):
        async with dynamodb_pessimistic_lock(key):
            pass

    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item.get("Item") is None
