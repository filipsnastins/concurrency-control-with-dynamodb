import uuid

import pytest
from pytest_mock import MockerFixture
from types_aiobotocore_dynamodb import DynamoDBClient

from database_locks import DynamoDBPessimisticLock, PessimisticLockError


def mock_now(mocker: MockerFixture, now: str) -> None:
    mocker.patch("database_locks.pessimistic_lock.now", return_value=now)


def generate_dynamodb_item_key() -> dict:
    return {"PK": {"S": f"ITEM#{uuid.uuid4()}"}, "SK": {"S": "ITEM"}}


async def create_dynamodb_item(localstack_dynamodb_client: DynamoDBClient, dynamodb_table_name: str, key: dict) -> None:
    await localstack_dynamodb_client.put_item(
        TableName=dynamodb_table_name,
        Item={
            **key,
            "Id": {"S": "123456"},
            "Name": {"S": "Test Name"},
        },
    )


@pytest.mark.asyncio()
async def test_should_not_create_not_existing_item__on_lock_acquisition(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_dynamodb_item_key()

    with pytest.raises(PessimisticLockError, match=str(key)):
        async with dynamodb_pessimistic_lock(key):
            pass

    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item.get("Item") is None


@pytest.mark.asyncio()
async def test_should_not_create_not_existing_item__on_lock_release(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)

    with pytest.raises(PessimisticLockError):  # noqa: PT012
        async with dynamodb_pessimistic_lock(key):
            await localstack_dynamodb_client.delete_item(TableName=dynamodb_table_name, Key=key)

    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item.get("Item") is None


@pytest.mark.asyncio()
async def test_should_set_and_remove_lock_attribute(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    mocker: MockerFixture,
) -> None:
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)
    mock_now(mocker, "2024-01-27T09:59:24.868868+00:00")

    async with dynamodb_pessimistic_lock(key):
        item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
        assert item["Item"] == {
            **key,
            "Id": {"S": "123456"},
            "Name": {"S": "Test Name"},
            "__LockedAt": {"S": "2024-01-27T09:59:24.868868+00:00"},
        }

    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item["Item"] == {
        **key,
        "Id": {"S": "123456"},
        "Name": {"S": "Test Name"},
    }


@pytest.mark.asyncio()
async def test_should_raise_if_lock_already_acquired(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)

    async with dynamodb_pessimistic_lock(key):
        with pytest.raises(PessimisticLockError):
            async with dynamodb_pessimistic_lock(key):
                pass


@pytest.mark.asyncio()
async def test_should_release_lock_on_exception(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)

    with pytest.raises(RuntimeError):  # noqa: PT012
        async with dynamodb_pessimistic_lock(key):
            raise RuntimeError

    async with dynamodb_pessimistic_lock(key):
        pass


# TODO: discard stale lock
# TODO: change lock attribute name
# TODO: release lock on exception
