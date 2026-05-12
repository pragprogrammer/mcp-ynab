# Field Reference

Every YNAB MCP tool that returns a model accepts an optional `exclude_fields` parameter.

> **Money fields** (e.g. `amount`, `balance`, `budgeted`, `activity`, `income`, `goal_target`) are returned as **dollar floats** with 3-decimal precision (e.g. `-50.25`, `1234.567`). YNAB's underlying milliunit integer (1000 = $1.00) is preserved internally - the conversion happens only on serialization. Tool inputs that accept money still take dollar floats.

## How `exclude_fields` works

| Value | Behavior |
|---|---|
| Not passed (`None`) | The model's **default** exclude list is applied (see below per model). This is what you want most of the time — sensible defaults that hide noisy fields. |
| `[]` (empty list) | **All fields** are returned. Use this when you need the complete model. |
| Custom list (e.g. `["foo", "bar"]`) | **Only your list** is excluded. Defaults are ignored. To exclude more than the default, copy the default list, add your extras, and pass that. |

> **Tip for agents**: don't pass `exclude_fields` unless you actually want fields the default hides. The default is tuned to give you the most useful information for the lowest token cost.

## Per-model field reference

### Account

**All fields**: `id`, `name`, `type`, `on_budget`, `closed`, `note`, `balance`,
`cleared_balance`, `uncleared_balance`, `transfer_payee_id`, `direct_import_linked`,
`direct_import_in_error`, `last_reconciled_at`, `debt_original_balance`,
`debt_interest_rates`, `debt_minimum_payments`, `debt_escrow_amounts`, `deleted`

**Default `exclude_fields`**:
```json
["direct_import_linked", "direct_import_in_error", "last_reconciled_at",
 "debt_original_balance", "debt_interest_rates", "debt_minimum_payments",
 "debt_escrow_amounts", "deleted"]
```

### Transaction

**All fields**: `id`, `date`, `amount`, `memo`, `cleared`, `approved`, `flag_color`,
`flag_name`, `account_id`, `account_name`, `payee_id`, `payee_name`, `category_id`,
`category_name`, `transfer_account_id`, `transfer_transaction_id`,
`matched_transaction_id`, `import_id`, `import_payee_name`, `import_payee_name_original`,
`debt_transaction_type`, `subtransactions`, `deleted`

**Default `exclude_fields`**:
```json
["flag_name", "import_id", "import_payee_name", "import_payee_name_original",
 "matched_transaction_id", "transfer_transaction_id", "debt_transaction_type",
 "deleted"]
```

### HybridTransaction

Returned by `get_transactions_by_category` and `get_transactions_by_payee`. Same
fields as `Transaction` plus `type` (`"transaction"` or `"subtransaction"`) and
`parent_transaction_id` (set on subtransaction rows). No `subtransactions` field —
splits are flattened into separate rows.

**Default `exclude_fields`**: same as `Transaction`.

### Subtransaction

Nested inside `Transaction.subtransactions` for split transactions.

**All fields**: `id`, `transaction_id`, `amount`, `memo`, `payee_id`, `payee_name`,
`category_id`, `category_name`, `transfer_account_id`, `transfer_transaction_id`,
`deleted`

**Default `exclude_fields`**: `["transfer_account_id", "transfer_transaction_id", "deleted"]`

### Category

**All fields**: `id`, `category_group_id`, `category_group_name`, `name`, `hidden`,
`original_category_group_id`, `note`, `budgeted`, `activity`, `balance`, `goal_type`,
`goal_needs_whole_amount`, `goal_day`, `goal_cadence`, `goal_cadence_frequency`,
`goal_creation_month`, `goal_target`, `goal_target_month`, `goal_target_date`,
`goal_percentage_complete`, `goal_months_to_budget`, `goal_under_funded`,
`goal_overall_funded`, `goal_overall_left`, `goal_snoozed_at`, `deleted`

**Default `exclude_fields`**:
```json
["original_category_group_id", "goal_target_month", "goal_creation_month",
 "goal_snoozed_at", "goal_needs_whole_amount", "goal_day", "goal_cadence",
 "goal_cadence_frequency", "deleted"]
```

`original_category_group_id` and `goal_target_month` are deprecated by YNAB. The
goal cadence/day fields are advanced and rarely needed; the goal target/progress
fields (`goal_target`, `goal_target_date`, `goal_percentage_complete`,
`goal_under_funded`, `goal_overall_funded`, `goal_overall_left`,
`goal_months_to_budget`) are kept by default since they're what most agents need
for budgeting analysis.

### CategoryGroup

**All fields**: `id`, `name`, `hidden`, `deleted`, `categories`

**Default `exclude_fields`**: `["deleted"]`

### MonthSummary / MonthDetail

**MonthSummary fields**: `month`, `note`, `income`, `budgeted`, `activity`,
`to_be_budgeted`, `age_of_money`, `deleted`

**MonthDetail fields**: same as MonthSummary plus `categories` (list of `Category`).

**Default `exclude_fields`**: `["deleted"]`

### Payee

**All fields**: `id`, `name`, `transfer_account_id`, `deleted`

**Default `exclude_fields`**: `["deleted"]`

### PayeeLocation

**All fields**: `id`, `payee_id`, `latitude`, `longitude`, `deleted`

**Default `exclude_fields`**: `["deleted"]`

### ScheduledTransaction

**All fields**: `id`, `date_first`, `date_next`, `frequency`, `amount`, `memo`,
`flag_color`, `flag_name`, `account_id`, `account_name`, `payee_id`, `payee_name`,
`category_id`, `category_name`, `transfer_account_id`, `subtransactions`, `deleted`

**Default `exclude_fields`**: `["flag_name", "deleted"]`

### ScheduledSubtransaction

**All fields**: `id`, `scheduled_transaction_id`, `amount`, `memo`, `payee_id`,
`payee_name`, `category_id`, `category_name`, `transfer_account_id`, `deleted`

**Default `exclude_fields`**: `["deleted"]`

### MoneyMovement

**All fields**: `id`, `month`, `moved_at`, `note`, `money_movement_group_id`,
`performed_by_user_id`, `from_category_id`, `to_category_id`, `amount`

**Default `exclude_fields`**: `[]` (model is already lean)

### MoneyMovementGroup

**All fields**: `id`, `group_created_at`, `month`, `note`, `performed_by_user_id`

**Default `exclude_fields`**: `[]` (model is already lean)

### PlanSummary / PlanDetail

**PlanSummary fields**: `id`, `name`, `last_modified_on`, `first_month`, `last_month`,
`date_format`, `currency_format`, `accounts`

**PlanDetail fields**: PlanSummary fields plus full nested entity exports (`payees`,
`payee_locations`, `category_groups`, `categories`, `months`, `transactions`,
`subtransactions`, `scheduled_transactions`, `scheduled_subtransactions`).

**Default `exclude_fields`**: `["last_modified_on"]`

`PlanDetail` is intentionally a full-export endpoint — its nested lists are NOT
trimmed by the plan-level default exclude. The nested entities are serialized with
their own model defaults if you serialize them individually, but when wrapped in
`PlanDetail` they appear in full.

### PlanSettings

**All fields**: `date_format`, `currency_format`

**Default `exclude_fields`**: `[]` (only 2 fields)

### User

**All fields**: `id`

**Default `exclude_fields`**: `[]`

## Examples

### Get an account with all fields including debt info

```python
get_account(account_id="...", plan_id="...", exclude_fields=[])
```

### Get transactions but also keep `import_id` (for audit trails)

Copy the default exclude list and remove `import_id`:

```python
list_transactions(
    plan_id="...",
    exclude_fields=[
        "flag_name",
        "import_payee_name",
        "import_payee_name_original",
        "matched_transaction_id",
        "transfer_transaction_id",
        "debt_transaction_type",
        "deleted",
    ],
)
```

### Strip a category response down to just the goal data

```python
get_category_for_month(
    category_id="...",
    month="current",
    plan_id="...",
    exclude_fields=[
        "category_group_id", "category_group_name", "hidden", "note",
        "budgeted", "activity", "balance", "deleted",
        "original_category_group_id", "goal_target_month",
        "goal_creation_month", "goal_snoozed_at", "goal_needs_whole_amount",
        "goal_day", "goal_cadence", "goal_cadence_frequency",
    ],
)
```
