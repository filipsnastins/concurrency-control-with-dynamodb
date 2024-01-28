# database-locks-dynamodb

work in progress 🚧

## Pessimistic Locks

- To ensure an operation is performed once - by acquiring an exclusive lock on a resource.
  - If an operation has a side effect, e.g., sending an external HTTP request.
  - For example, when sending an HTTP request to a payment gateway once at a time.

## Optimistic Lock

- In message driven architecture when used together with transactional outbox

  - If external services are wrapped in their own services/message consumers - request/response over messages

- <https://aws.amazon.com/blogs/database/implement-resource-counters-with-amazon-dynamodb/>
