import datetime
import uuid
from unittest import mock

import pytest
from pytest_mock import MockerFixture
from types_aiobotocore_dynamodb import DynamoDBClient

from adapters.dynamodb import create_table
from database_locks import DynamoDBPessimisticLock, PessimisticLockAcquisitionError, PessimisticLockItemNotFoundError


def mock_time_now(mocker: MockerFixture, now: str) -> None:
    return_value = datetime.datetime.fromisoformat(now).replace(tzinfo=datetime.UTC)
    mocker.patch("database_locks.pessimistic_lock.now", return_value=return_value)


def generate_dynamodb_item_key(*, with_range_key: bool = True) -> dict:
    if with_range_key:
        return {"PK": {"S": f"ITEM#{uuid.uuid4()}"}, "SK": {"S": "ITEM"}}
    return {"PK": {"S": f"ITEM#{uuid.uuid4()}"}}


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

    with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
        async with dynamodb_pessimistic_lock(key):
            pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover

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

    with pytest.raises(PessimisticLockItemNotFoundError):  # noqa: PT012
        async with dynamodb_pessimistic_lock(key):
            await localstack_dynamodb_client.delete_item(TableName=dynamodb_table_name, Key=key)

    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item.get("Item") is None


@pytest.mark.asyncio()
async def test_should_raise_if_lock_not_acquired_and_not_release_existing_lock(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)

    async with dynamodb_pessimistic_lock(key):
        with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
            async with dynamodb_pessimistic_lock(key):
                pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover

        with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
            async with dynamodb_pessimistic_lock(key):
                pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover


@pytest.mark.asyncio()
async def test_should_release_lock_on_context_exit(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
) -> None:
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)

    async with dynamodb_pessimistic_lock(key):
        pass

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


@pytest.mark.asyncio()
async def test_should_set_and_remove_lock_attribute(
    dynamodb_pessimistic_lock: DynamoDBPessimisticLock,
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    mocker: MockerFixture,
) -> None:
    # Arrange
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)
    mock_time_now(mocker, "2024-01-27T09:01:02+00:00")

    # Act
    async with dynamodb_pessimistic_lock(key):
        # Assert
        item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
        assert item["Item"] == {
            **key,
            "Id": {"S": "123456"},
            "Name": {"S": "Test Name"},
            "__LockedAt": {"S": "2024-01-27T09:01:02+00:00"},
        }

    # Assert
    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item["Item"] == {
        **key,
        "Id": {"S": "123456"},
        "Name": {"S": "Test Name"},
    }


@pytest.mark.asyncio()
async def test_configurable_lock_attribute(
    localstack_dynamodb_client: DynamoDBClient, dynamodb_table_name: str
) -> None:
    # Arrange
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)
    dynamodb_pessimistic_lock = DynamoDBPessimisticLock(
        localstack_dynamodb_client, dynamodb_table_name, lock_attribute="__MyLockAttribute"
    )

    # Act
    async with dynamodb_pessimistic_lock(key):
        # Assert
        item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
        assert item["Item"] == {
            **key,
            "Id": {"S": "123456"},
            "Name": {"S": "Test Name"},
            "__MyLockAttribute": {"S": mock.ANY},
        }

    # Assert
    item = await localstack_dynamodb_client.get_item(TableName=dynamodb_table_name, Key=key)
    assert item["Item"] == {
        **key,
        "Id": {"S": "123456"},
        "Name": {"S": "Test Name"},
    }


@pytest.mark.parametrize(
    ("now", "future", "lock_timeout"),
    [
        ("2024-01-27T09:00:00+00:00", "2127-02-28T00:00:00+00:00", None),
        ("2024-01-27T09:00:00+00:00", "2024-01-27T10:59:59+00:00", datetime.timedelta(hours=2)),
        ("2024-01-27T09:00:00+00:00", "2024-01-27T11:00:00+00:00", datetime.timedelta(hours=2)),
    ],
)
@pytest.mark.asyncio()
async def test_should_not_discard_stale_lock_when_lock_timeout_has_not_expired(
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    mocker: MockerFixture,
    now: str,
    future: str,
    lock_timeout: datetime.timedelta | None,
) -> None:
    # Arrange
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)
    dynamodb_pessimistic_lock = DynamoDBPessimisticLock(
        localstack_dynamodb_client, dynamodb_table_name, lock_timeout=lock_timeout
    )

    # Act
    mock_time_now(mocker, now)

    async with dynamodb_pessimistic_lock(key):
        mock_time_now(mocker, future)

        # Assert
        with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
            async with dynamodb_pessimistic_lock(key):
                pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover

        with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
            async with dynamodb_pessimistic_lock(key):
                pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover


@pytest.mark.parametrize(
    ("now", "future", "lock_timeout"),
    [
        ("2024-01-27T09:00:00+00:00", "2024-01-27T11:00:01+00:00", datetime.timedelta(hours=2)),
        ("2024-01-27T09:00:00+00:00", "2024-01-27T11:01:00+00:00", datetime.timedelta(hours=2)),
    ],
)
@pytest.mark.asyncio()
async def test_should_discard_stale_lock_when_lock_timeout_has_expired(
    localstack_dynamodb_client: DynamoDBClient,
    dynamodb_table_name: str,
    mocker: MockerFixture,
    now: str,
    future: str,
    lock_timeout: datetime.timedelta,
) -> None:
    # Arrange
    key = generate_dynamodb_item_key()
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)
    dynamodb_pessimistic_lock = DynamoDBPessimisticLock(
        localstack_dynamodb_client, dynamodb_table_name, lock_timeout=lock_timeout
    )

    # Act
    mock_time_now(mocker, now)

    async with dynamodb_pessimistic_lock(key):
        mock_time_now(mocker, future)

        # Assert
        async with dynamodb_pessimistic_lock(key):
            pass

        async with dynamodb_pessimistic_lock(key):
            pass


@pytest.mark.asyncio()
async def test_should_lock_and_unlock_item_with_only_partition_key(localstack_dynamodb_client: DynamoDBClient) -> None:
    # Arrange
    dynamodb_table_name = f"autotest-dynamodb-pessimistic-lock-{uuid.uuid4()}"
    await create_table(localstack_dynamodb_client, dynamodb_table_name, with_range_key=False)

    key = generate_dynamodb_item_key(with_range_key=False)
    await create_dynamodb_item(localstack_dynamodb_client, dynamodb_table_name, key)

    dynamodb_pessimistic_lock = DynamoDBPessimisticLock(localstack_dynamodb_client, dynamodb_table_name)

    # Act
    async with dynamodb_pessimistic_lock(key):
        # Assert
        with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
            async with dynamodb_pessimistic_lock(key):
                pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover

        with pytest.raises(PessimisticLockAcquisitionError):  # noqa: PT012
            async with dynamodb_pessimistic_lock(key):
                pytest.fail(reason="Executed code without acquiring lock")  # pragma: no cover

    async with dynamodb_pessimistic_lock(key):
        pass
