from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.db.types import EncryptedJSON
from src.models.common import YNABBaseModel

T = TypeVar("T", bound=YNABBaseModel)


class Base(DeclarativeBase):
    pass


class CachedEntity(Base):
    __tablename__ = "cached_entity"
    __table_args__ = (UniqueConstraint("plan_id", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String)
    # Encrypted: this is the whole entity, amounts and payees and memos included.
    # The columns above stay plaintext because lookups and delta sync need them.
    data: Mapped[Any] = mapped_column(EncryptedJSON("cached_entity", "data"))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def from_model(cls, plan_id: str, entity_type: str, model: YNABBaseModel) -> "CachedEntity":
        data = model.model_dump()
        return cls(
            plan_id=plan_id,
            entity_type=entity_type,
            entity_id=data.get("id", ""),
            data=data,
            is_deleted=data.get("deleted", False),
            cached_at=datetime.now(timezone.utc),
        )

    def to_model(self, model_class: type[T]) -> T:
        return model_class.model_validate(self.data)

    def update_from_model(self, model: YNABBaseModel) -> None:
        data = model.model_dump()
        self.data = data
        self.is_deleted = data.get("deleted", False)
        self.cached_at = datetime.now(timezone.utc)


class ServerKnowledge(Base):
    __tablename__ = "server_knowledge"
    __table_args__ = (UniqueConstraint("plan_id", "endpoint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(String)
    endpoint: Mapped[str] = mapped_column(String)
    knowledge: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class ResponseCache(Base):
    __tablename__ = "response_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    data: Mapped[Any] = mapped_column(EncryptedJSON("response_cache", "data"))
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
    def from_model_list(cls, cache_key: str, models: Sequence[YNABBaseModel], ttl: int) -> "ResponseCache":
        return cls(
            cache_key=cache_key,
            data=[m.model_dump() for m in models],
            cached_at=datetime.now(timezone.utc),
            ttl_seconds=ttl,
        )

    def to_model(self, model_class: type[T]) -> T:
        return model_class.model_validate(self.data)

    def to_model_list(self, model_class: type[T]) -> list[T]:
        return [model_class.model_validate(d) for d in self.data]

    def update_from_model(self, model: YNABBaseModel) -> None:
        self.data = model.model_dump()
        self.cached_at = datetime.now(timezone.utc)

    def update_from_model_list(self, models: Sequence[YNABBaseModel]) -> None:
        self.data = [m.model_dump() for m in models]
        self.cached_at = datetime.now(timezone.utc)
