# Task ids are never reused after a deletion

Deleting a Task does not release its id. Phase 3 of the guide leaves this open ("reuse it or never reuse it, either is fine"), but the phases after it depend on non-reuse: the Phase 8 contract test asserts that a Task added after a deletion gets a higher id than the deleted one, and the Phase 9 schema uses `AUTOINCREMENT`, which never reuses a rowid. Reuse would also break any client holding an id, because after the deletion the same number would point at a different Task.

## Consequences

Part 1 cannot use the guide's Phase 1 rule of "the highest existing id plus 1", because deleting the highest Task would make the next Task reuse that id. The JSON file therefore carries a `next_id` counter from its first version. That is the same counter the guide introduces later, in Phase 8, pulled forward so Part 1 already satisfies Part 2's contract.

Task also takes its title first and its id second, with the id defaulting to `None`, because a task can exist before a store gives it an id. The guide writes the constructor the other way round in Phase 3 and then builds a task without an id in Phase 8, so the two orders cannot both be right.
