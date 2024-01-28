# TODOs

## Code

- [x] `database_locks`

  - [x] `pessimistic_lock`

- [x] `pessimistic_payments`

- [ ] `optimistic_payments`

  - [x] Update amount use case
  - [ ] Charge Payment Intent use case - with optimistic & semantic locks
  - [ ] Update `PaymentIntent.version` in-place in `DynamoDBPaymentIntentRepository.update`?

- [x] `__eq__` method on aggregate objects?

  - [ ] `test_domain.py`

- [ ] Idempotence keys

## Docs

- [ ] README

- [ ] Using pessimistic and optimistic locks together
