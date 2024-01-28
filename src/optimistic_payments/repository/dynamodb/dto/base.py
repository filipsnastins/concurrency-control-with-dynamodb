import abc
from typing import Generic, Self, TypeVar

import boto3.dynamodb.types
from pydantic import BaseModel
from types_aiobotocore_dynamodb.type_defs import AttributeValueTypeDef

BOTO3_DESERIALIZER = boto3.dynamodb.types.TypeDeserializer()
BOTO3_SERIALIZER = boto3.dynamodb.types.TypeSerializer()


AggregateType = TypeVar("AggregateType")


class BaseDTO(BaseModel, Generic[AggregateType]):
    @classmethod
    @abc.abstractmethod
    def from_aggregate(cls: type[Self], aggregate: AggregateType) -> Self:
        pass  # pragma: no cover

    @classmethod
    def from_dynamodb_item(cls: type[Self], item: dict[str, AttributeValueTypeDef]) -> Self:
        return cls(**{k: BOTO3_DESERIALIZER.deserialize(v) for k, v in item.items()})

    @abc.abstractmethod
    def to_aggregate(self) -> AggregateType:
        pass  # pragma: no cover

    def to_dynamodb_item(self) -> dict[str, AttributeValueTypeDef]:
        return {k: BOTO3_SERIALIZER.serialize(v) for k, v in self.model_dump().items()}
