from contextlib import suppress

from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_dynamodb.type_defs import AttributeDefinitionTypeDef, KeySchemaElementTypeDef


async def create_table(client: DynamoDBClient, table_name: str, *, with_range_key: bool) -> None:
    with suppress(client.exceptions.ResourceInUseException):
        attribute_definitions: list[AttributeDefinitionTypeDef] = [{"AttributeName": "PK", "AttributeType": "S"}]
        key_schema: list[KeySchemaElementTypeDef] = [{"AttributeName": "PK", "KeyType": "HASH"}]

        if with_range_key:
            attribute_definitions.append({"AttributeName": "SK", "AttributeType": "S"})
            key_schema.append({"AttributeName": "SK", "KeyType": "RANGE"})

        await client.create_table(
            TableName=table_name,
            AttributeDefinitions=attribute_definitions,
            KeySchema=key_schema,
            BillingMode="PAY_PER_REQUEST",
        )
