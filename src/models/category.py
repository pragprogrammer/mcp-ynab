from pydantic import Field

from src.models.common import YNABBaseModel

# Fields excluded from the standard category list display
CATEGORY_LIST_EXCLUDE = {"category_group_id", "category_group_name",
                         "goal_type", "goal_target", "goal_percentage_complete", "deleted"}

# Fields included in the category detail display (get_category_for_month)
CATEGORY_DETAIL_INCLUDE = {"id", "name", "budgeted", "activity", "balance",
                           "goal_type", "goal_target", "goal_percentage_complete"}


class Category(YNABBaseModel):
    id: str = Field()
    category_group_id: str = Field()
    category_group_name: str | None = Field(default=None)
    name: str = Field()
    hidden: bool = Field(default=False)
    budgeted: int = Field(default=0)
    activity: int = Field(default=0)
    balance: int = Field(default=0)
    goal_type: str | None = Field(default=None)
    goal_target: int | None = Field(default=None)
    goal_percentage_complete: int | None = Field(default=None)
    deleted: bool = Field(default=False)


class CategoryGroup(YNABBaseModel):
    id: str = Field()
    name: str = Field()
    hidden: bool = Field(default=False)
    deleted: bool = Field(default=False)
    categories: list[Category] = Field(default=[])
