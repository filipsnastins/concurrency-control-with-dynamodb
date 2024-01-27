import asyncio
from contextlib import closing
from typing import Generator, Iterator, cast

import pytest
from tomodachi_testcontainers import DynamoDBAdminContainer, LocalStackContainer


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    with closing(asyncio.new_event_loop()) as loop:
        yield loop


@pytest.fixture(scope="session", autouse=True)
def dynamodb_admin_container(
    localstack_container: LocalStackContainer,
) -> Generator[DynamoDBAdminContainer, None, None]:
    with DynamoDBAdminContainer(dynamo_endpoint=localstack_container.get_internal_url()) as container:
        yield cast(DynamoDBAdminContainer, container)
