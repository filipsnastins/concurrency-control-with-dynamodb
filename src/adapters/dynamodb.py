from contextlib import suppress

from types_aiobotocore_dynamodb import DynamoDBClient


async def create_table(client: DynamoDBClient, table_name: str) -> None:
    with suppress(client.exceptions.ResourceInUseException):
        await client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
