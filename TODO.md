# TODOs

## Code

- [x] `database_locks`

  - [x] `pessimistic_lock`

- [x] `pessimistic_payments`

  - [ ] Optimistic lock can't be used in combination with pessimistic lock?
    - `change_payment_intent_amount` with optimistic lock can't prevent concurrent updates with `charge_payment_intent` with pessimistic lock

- [ ] `optimistic_payments`

  - [x] Update amount use case

  - [x] Charge Payment Intent use case - with optimistic & semantic locks

  - [ ] Update `PaymentIntent.version` in-place in `DynamoDBPaymentIntentRepository.update`?

  - [ ] Consistent read is no longer needed because the optimistic lock will ensure a stale aggregate update is rejected

- [x] `__eq__` method on aggregate objects?

  - [ ] `test_domain.py`

- [ ] Idempotence keys

## Docs

- [ ] README
