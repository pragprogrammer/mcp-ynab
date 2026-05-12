from src.models import (
    Account,
    PlanDetail,
    PlanSummary,
    Category,
    CategoryGroup,
    MonthDetail,
    MonthSummary,
    Payee,
    ScheduledTransaction,
    Transaction,
)
from src.models.account import ACCOUNT_DEFAULT_EXCLUDE
from src.models.category import CATEGORY_DEFAULT_EXCLUDE
from src.models.month import MONTH_DEFAULT_EXCLUDE
from src.models.payee import PAYEE_DEFAULT_EXCLUDE
from src.models.plan import PLAN_DEFAULT_EXCLUDE
from src.models.scheduled_transaction import SCHEDULED_TRANSACTION_DEFAULT_EXCLUDE
from src.models.transaction import TRANSACTION_DEFAULT_EXCLUDE


class TestTransaction:
    def test_default_exclude_keeps_useful_fields(self):
        t = Transaction(id="t1", date="2026-03-15", amount=-50250,
                        account_name="Checking", payee_name="Store", category_name="Food")
        result = t.model_dump(by_alias=True, exclude=TRANSACTION_DEFAULT_EXCLUDE)
        assert result["amount"] == -50250
        assert result["account_name"] == "Checking"
        assert result["payee_name"] == "Store"
        assert result["category_name"] == "Food"

    def test_default_exclude_hides_noisy_fields(self):
        t = Transaction(id="t1", date="2026-03-15", deleted=True,
                        import_id="imp1", flag_name="Red",
                        matched_transaction_id="m1", debt_transaction_type="payment")
        result = t.model_dump(by_alias=True, exclude=TRANSACTION_DEFAULT_EXCLUDE)
        for hidden in ["deleted", "import_id", "import_payee_name",
                       "import_payee_name_original", "flag_name",
                       "matched_transaction_id", "transfer_transaction_id",
                       "debt_transaction_type"]:
            assert hidden not in result

    def test_roundtrip_preserves_all_fields(self):
        t = Transaction(id="t1", date="2026-03-15", amount=-50250,
                         account_id="a1", payee_name="Store", category_id="c1")
        raw = t.model_dump()
        t2 = Transaction.model_validate(raw)
        assert t2.amount == -50250
        assert t2.account_id == "a1"
        assert t2.category_id == "c1"

    def test_extra_fields_ignored(self):
        t = Transaction(id="t1", date="2026-03-15", some_new_api_field="surprise")
        assert not hasattr(t, "some_new_api_field")


class TestAccount:
    def test_default_exclude_hides_noisy_fields(self):
        a = Account(id="a1", name="Checking", type="checking", deleted=True)
        result = a.model_dump(by_alias=True, exclude=ACCOUNT_DEFAULT_EXCLUDE)
        for hidden in ["deleted", "direct_import_linked", "direct_import_in_error",
                       "last_reconciled_at", "debt_original_balance",
                       "debt_interest_rates", "debt_minimum_payments",
                       "debt_escrow_amounts"]:
            assert hidden not in result
        assert "id" in result
        assert "name" in result
        assert "balance" in result

    def test_roundtrip_preserves_deleted(self):
        a = Account(id="a1", name="Checking", type="checking", deleted=True)
        raw = a.model_dump()
        a2 = Account.model_validate(raw)
        assert a2.deleted is True


class TestCategory:
    def test_default_exclude_hides_advanced_goal_fields(self):
        c = Category(id="c1", category_group_id="g1", name="Food",
                     goal_type="TB", goal_target=500000, goal_cadence=1,
                     goal_day=15, deleted=True)
        result = c.model_dump(by_alias=True, exclude=CATEGORY_DEFAULT_EXCLUDE)
        for hidden in ["deleted", "original_category_group_id", "goal_target_month",
                       "goal_creation_month", "goal_snoozed_at",
                       "goal_needs_whole_amount", "goal_day", "goal_cadence",
                       "goal_cadence_frequency"]:
            assert hidden not in result
        assert result["goal_type"] == "TB"
        assert result["goal_target"] == 500000

    def test_roundtrip_preserves_all_fields(self):
        c = Category(id="c1", category_group_id="g1", name="Food", budgeted=500000)
        raw = c.model_dump()
        c2 = Category.model_validate(raw)
        assert c2.budgeted == 500000
        assert c2.category_group_id == "g1"


class TestCategoryGroup:
    def test_display_dump_excludes_deleted(self):
        group = CategoryGroup(id="g1", name="Bills", deleted=True)
        result = group.model_dump(by_alias=True, exclude={"deleted"})
        assert "deleted" not in result

    def test_nested_categories_serialize(self):
        cat = Category(id="c1", category_group_id="g1", name="Food", budgeted=500000)
        group = CategoryGroup(id="g1", name="Bills", categories=[cat])
        result = group.model_dump(by_alias=True, exclude={"deleted"})
        assert len(result["categories"]) == 1
        assert result["categories"][0]["name"] == "Food"


class TestPlanSummary:
    def test_default_exclude_hides_last_modified(self):
        b = PlanSummary(id="b1", name="My Budget", last_modified_on="2026-03-15")
        result = b.model_dump(by_alias=True, exclude=PLAN_DEFAULT_EXCLUDE)
        assert result["id"] == "b1"
        assert result["name"] == "My Budget"
        assert "last_modified_on" not in result


class TestPlanDetail:
    def test_roundtrip(self):
        b = PlanDetail(id="b1", name="My Budget", last_modified_on="2026-03-15")
        result = b.model_dump(by_alias=True)
        assert result["id"] == "b1"
        assert result["last_modified_on"] == "2026-03-15"


class TestPayee:
    def test_default_exclude_hides_deleted(self):
        p = Payee(id="p1", name="Amazon", transfer_account_id="ta1")
        result = p.model_dump(by_alias=True, exclude=PAYEE_DEFAULT_EXCLUDE)
        assert result["id"] == "p1"
        assert result["name"] == "Amazon"
        assert result["transfer_account_id"] == "ta1"
        assert "deleted" not in result


class TestMonthSummary:
    def test_default_exclude_hides_deleted(self):
        m = MonthSummary(month="2026-03-01", deleted=True, age_of_money=45)
        result = m.model_dump(by_alias=True, exclude=MONTH_DEFAULT_EXCLUDE)
        assert "deleted" not in result
        assert "note" in result
        assert result["age_of_money"] == 45

    def test_roundtrip_preserves_values(self):
        m = MonthSummary(month="2026-03-01", income=5000000, deleted=True)
        raw = m.model_dump()
        m2 = MonthSummary.model_validate(raw)
        assert m2.income == 5000000
        assert m2.deleted is True


class TestMonthDetail:
    def test_default_exclude_keeps_categories(self):
        cat = Category(id="c1", category_group_id="g1", name="Food", budgeted=500000)
        m = MonthDetail(month="2026-03-01", income=5000000, categories=[cat])
        result = m.model_dump(by_alias=True, exclude=MONTH_DEFAULT_EXCLUDE)
        assert result["income"] == 5000000
        assert len(result["categories"]) == 1
        assert "note" in result
        assert "age_of_money" in result
        assert "deleted" not in result


class TestScheduledTransaction:
    def test_default_exclude_keeps_useful_fields(self):
        st = ScheduledTransaction(
            id="st1", date_next="2026-04-01", frequency="monthly",
            amount=-100000, payee_name="Netflix", category_name="Entertainment",
            account_name="Checking",
        )
        result = st.model_dump(by_alias=True, exclude=SCHEDULED_TRANSACTION_DEFAULT_EXCLUDE)
        assert result["amount"] == -100000
        assert result["payee_name"] == "Netflix"
        assert result["category_name"] == "Entertainment"
        assert result["account_name"] == "Checking"

    def test_default_exclude_hides_noisy_fields(self):
        st = ScheduledTransaction(id="st1", deleted=True, account_id="a1",
                                  payee_id="p1", category_id="c1")
        result = st.model_dump(by_alias=True, exclude=SCHEDULED_TRANSACTION_DEFAULT_EXCLUDE)
        assert "deleted" not in result
        assert "flag_name" not in result
        # Other fields stay
        for field in ["account_id", "payee_id", "category_id", "subtransactions"]:
            assert field in result


class TestUser:
    def test_roundtrip(self):
        from src.models.user import User
        u = User(id="user-123")
        raw = u.model_dump()
        u2 = User.model_validate(raw)
        assert u2.id == "user-123"


class TestMilliunit:
    def test_amount_serializes_to_dollars_in_json_mode(self):
        t = Transaction(id="t1", date="2026-03-15", amount=-50250)
        result = t.model_dump(by_alias=True, mode="json")
        assert result["amount"] == -50.25

    def test_python_mode_dump_keeps_int(self):
        t = Transaction(id="t1", date="2026-03-15", amount=-50250)
        result = t.model_dump(by_alias=True)
        assert result["amount"] == -50250

    def test_attribute_access_returns_int(self):
        t = Transaction(id="t1", date="2026-03-15", amount=-50250)
        assert t.amount == -50250
        assert isinstance(t.amount, int)

    def test_optional_milliunit_none_passes_through(self):
        a = Account(id="a1", name="Checking", type="checking", debt_original_balance=None)
        result = a.model_dump(by_alias=True, mode="json")
        assert result["debt_original_balance"] is None

    def test_3_decimal_precision_preserves_non_usd_currencies(self):
        # KWD has 3 decimal digits; e.g. 1.234 KWD = 1234 milliunits
        t = Transaction(id="t1", date="2026-03-15", amount=1234)
        result = t.model_dump(by_alias=True, mode="json")
        assert result["amount"] == 1.234

    def test_python_mode_roundtrip_preserves_milliunits(self):
        m = MonthSummary(month="2026-03-01", income=5000000)
        raw = m.model_dump()
        m2 = MonthSummary.model_validate(raw)
        assert m2.income == 5000000

    def test_nested_categories_convert_in_json_mode(self):
        cat = Category(id="c1", category_group_id="g1", name="Food", budgeted=500000)
        m = MonthDetail(month="2026-03-01", income=5000000, categories=[cat])
        result = m.model_dump(by_alias=True, mode="json")
        assert result["income"] == 5000.0
        assert result["categories"][0]["budgeted"] == 500.0
