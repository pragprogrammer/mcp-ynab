from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.models.common import YNABBaseModel


class Base(DeclarativeBase):
    pass


class CachedEntity(Base):
    __tablename__ = "cached_entities"
    __table_args__ = (UniqueConstraint("budget_id", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String)
    data: Mapped[dict] = mapped_column(JSON)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def from_model(cls, budget_id: str, entity_type: str, model: YNABBaseModel) -> "CachedEntity":
        data = model.model_dump()
        return cls(
            budget_id=budget_id,
            entity_type=entity_type,
            entity_id=data.get("id", ""),
            data=data,
            is_deleted=data.get("deleted", False),
            cached_at=datetime.now(timezone.utc),
        )

    def to_model(self, model_class: type[YNABBaseModel]) -> YNABBaseModel:
        return model_class.model_validate(self.data)

    def update_from_model(self, model: YNABBaseModel) -> None:
        data = model.model_dump()
        self.data = data
        self.is_deleted = data.get("deleted", False)
        self.cached_at = datetime.now(timezone.utc)


class ServerKnowledge(Base):
    __tablename__ = "server_knowledge"
    __table_args__ = (UniqueConstraint("budget_id", "endpoint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[str] = mapped_column(String)
    endpoint: Mapped[str] = mapped_column(String)
    knowledge: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class ResponseCache(Base):
    __tablename__ = "response_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    data: Mapped[dict] = mapped_column(JSON)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ttl_seconds: Mapped[int] = mapped_column(Integer)

    @classmethod
    def from_model(cls, cache_key: str, model: YNABBaseModel, ttl: int) -> "ResponseCache":
        return cls(
            cache_key=cache_key,
            data=model.model_dump(),
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=ttl,
        )

    @classmethod
    def from_model_list(cls, cache_key: str, models: list[YNABBaseModel], ttl: int) -> "ResponseCache":
        return cls(
            cache_key=cache_key,
            data=[m.model_dump() for m in models],
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=ttl,
        )

    def to_model(self, model_class: type[YNABBaseModel]) -> YNABBaseModel:
        return model_class.model_validate(self.data)

    def to_model_list(self, model_class: type[YNABBaseModel]) -> list[YNABBaseModel]:
        return [model_class.model_validate(d) for d in self.data]

    def update_from_model(self, model: YNABBaseModel) -> None:
        self.data = model.model_dump()
        self.cached_at = datetime.now(timezone.utc)

    def update_from_model_list(self, models: list[YNABBaseModel]) -> None:
        self.data = [m.model_dump() for m in models]
        self.cached_at = datetime.now(timezone.utc)
