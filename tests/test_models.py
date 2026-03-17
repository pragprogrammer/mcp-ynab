from src.models import (
    Account,
    BudgetDetail,
    BudgetSummary,
    Category,
    CategoryGroup,
    MonthDetail,
    MonthSummary,
    Payee,
    ScheduledTransaction,
    Transaction,
)
from src.models.account import ACCOUNT_DISPLAY_EXCLUDE
from src.models.budget import BUDGET_SUMMARY_DISPLAY_EXCLUDE
from src.models.category import CATEGORY_DETAIL_INCLUDE, CATEGORY_LIST_EXCLUDE
from src.models.month import MONTH_DISPLAY_EXCLUDE
from src.models.payee import PAYEE_DISPLAY_EXCLUDE
from src.models.transaction import SCHEDULED_TRANSACTION_DISPLAY_EXCLUDE, TRANSACTION_DISPLAY_EXCLUDE


class TestTransaction:
    def test_display_dump_keeps_amount_as_int(self):
        t = Transaction(id="t1", date="2026-03-15", amount=-50250)
        result = t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE)
        assert result["amount"] == -50250

    def test_display_dump_aliases_fields(self):
        t = Transaction(id="t1", date="2026-03-15", payee_name="Store",
                         category_name="Food", account_name="Checking")
        result = t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE)
        assert result["payee"] == "Store"
        assert result["category"] == "Food"
        assert result["account"] == "Checking"
        assert "payee_name" not in result

    def test_display_dump_excludes_internal_fields(self):
        t = Transaction(id="t1", date="2026-03-15", deleted=True, account_id="a1",
                         subtransactions=[], import_id="imp1", flag_name="Red")
        result = t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE)
        for excluded in ["deleted", "account_id", "subtransactions", "import_id", "flag_name"]:
            assert excluded not in result

    def test_display_dump_expected_keys(self):
        t = Transaction(id="t1", date="2026-03-15")
        result = t.model_dump(by_alias=True, exclude=TRANSACTION_DISPLAY_EXCLUDE)
        expected_keys = {"id", "date", "amount", "memo", "cleared", "approved",
                         "flag_color", "payee_id", "payee", "category_id", "category", "account"}
        assert set(result.keys()) == expected_keys

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
    def test_display_dump_excludes_deleted(self):
        a = Account(id="a1", name="Checking", type="checking", deleted=True)
        result = a.model_dump(by_alias=True, exclude=ACCOUNT_DISPLAY_EXCLUDE)
        assert "deleted" not in result

    def test_display_dump_expected_keys(self):
        a = Account(id="a1", name="Checking", type="checking")
        result = a.model_dump(by_alias=True, exclude=ACCOUNT_DISPLAY_EXCLUDE)
        expected_keys = {"id", "name", "type", "on_budget", "closed",
                         "balance", "cleared_balance", "uncleared_balance"}
        assert set(result.keys()) == expected_keys

    def test_roundtrip_preserves_deleted(self):
        a = Account(id="a1", name="Checking", type="checking", deleted=True)
        raw = a.model_dump()
        a2 = Account.model_validate(raw)
        assert a2.deleted is True


class TestCategory:
    def test_list_exclude_removes_internal_fields(self):
        c = Category(id="c1", category_group_id="g1", name="Food",
                     goal_type="TB", goal_target=500000, deleted=True)
        result = c.model_dump(by_alias=True, exclude=CATEGORY_LIST_EXCLUDE)
        for excluded in ["category_group_id", "category_group_name",
                         "goal_type", "goal_target", "goal_percentage_complete", "deleted"]:
            assert excluded not in result

    def test_detail_include_shows_goal_fields(self):
        c = Category(id="c1", category_group_id="g1", name="Food",
                     goal_type="TB", goal_target=500000, goal_percentage_complete=50)
        result = c.model_dump(by_alias=True, include=CATEGORY_DETAIL_INCLUDE)
        assert result["goal_type"] == "TB"
        assert result["goal_target"] == 500000
        assert result["goal_percentage_complete"] == 50
        assert "hidden" not in result

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


class TestBudgetSummary:
    def test_display_dump_only_id_and_name(self):
        b = BudgetSummary(id="b1", name="My Budget", last_modified_on="2026-03-15")
        result = b.model_dump(by_alias=True, exclude=BUDGET_SUMMARY_DISPLAY_EXCLUDE)
        assert result == {"id": "b1", "name": "My Budget"}


class TestBudgetDetail:
    def test_display_dump_aliases_last_modified(self):
        b = BudgetDetail(id="b1", name="My Budget", last_modified_on="2026-03-15")
        result = b.model_dump(by_alias=True)
        assert result["last_modified"] == "2026-03-15"
        assert "last_modified_on" not in result


class TestPayee:
    def test_display_dump_only_id_and_name(self):
        p = Payee(id="p1", name="Amazon", transfer_account_id="ta1")
        result = p.model_dump(by_alias=True, exclude=PAYEE_DISPLAY_EXCLUDE)
        assert result == {"id": "p1", "name": "Amazon"}


class TestMonthSummary:
    def test_display_dump_excludes_deleted(self):
        m = MonthSummary(month="2026-03-01", deleted=True)
        result = m.model_dump(by_alias=True, exclude=MONTH_DISPLAY_EXCLUDE)
        assert "deleted" not in result

    def test_roundtrip_preserves_values(self):
        m = MonthSummary(month="2026-03-01", income=5000000, deleted=True)
        raw = m.model_dump()
        m2 = MonthSummary.model_validate(raw)
        assert m2.income == 5000000
        assert m2.deleted is True


class TestMonthDetail:
    def test_display_dump_includes_categories(self):
        cat = Category(id="c1", category_group_id="g1", name="Food", budgeted=500000)
        m = MonthDetail(month="2026-03-01", income=5000000, categories=[cat])
        result = m.model_dump(by_alias=True, exclude=MONTH_DISPLAY_EXCLUDE)
        assert result["income"] == 5000000
        assert len(result["categories"]) == 1


class TestScheduledTransaction:
    def test_display_dump_aliases(self):
        st = ScheduledTransaction(
            id="st1", date_next="2026-04-01", frequency="monthly",
            amount=-100000, payee_name="Netflix", category_name="Entertainment",
            account_name="Checking",
        )
        result = st.model_dump(by_alias=True, exclude=SCHEDULED_TRANSACTION_DISPLAY_EXCLUDE)
        assert result["amount"] == -100000
        assert result["payee"] == "Netflix"
        assert result["category"] == "Entertainment"
        assert result["account"] == "Checking"

    def test_display_dump_excludes_internal_fields(self):
        st = ScheduledTransaction(id="st1", deleted=True, account_id="a1",
                                  payee_id="p1", category_id="c1")
        result = st.model_dump(by_alias=True, exclude=SCHEDULED_TRANSACTION_DISPLAY_EXCLUDE)
        for excluded in ["deleted", "account_id", "payee_id", "category_id",
                         "date_first", "flag_color", "flag_name", "subtransactions"]:
            assert excluded not in result
