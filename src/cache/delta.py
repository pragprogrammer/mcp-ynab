import logging
from datetime import datetime, timezone

from sqlalchemy import select

from src.db.engine import get_session
from src.db.tables import CachedEntity, ServerKnowledge
from src.models.common import YNABBaseModel

logger = logging.getLogger(__name__)


class DeltaSyncManager:
    def __init__(self, min_interval: int = 30):
        self.min_interval = min_interval

    async def should_sync(self, budget_id: str, endpoint: str) -> bool:
        async with get_session() as session:
            stmt = select(ServerKnowledge).where(
                ServerKnowledge.budget_id == budget_id,
                ServerKnowledge.endpoint == endpoint,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return True
            elapsed = (datetime.now(timezone.utc) - row.last_synced_at.replace(tzinfo=timezone.utc)).total_seconds()
            return elapsed >= self.min_interval

    async def get_knowledge(self, budget_id: str, endpoint: str) -> int | None:
        async with get_session() as session:
            stmt = select(ServerKnowledge).where(
                ServerKnowledge.budget_id == budget_id,
                ServerKnowledge.endpoint == endpoint,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return row.knowledge if row else None

    async def update_knowledge(self, budget_id: str, endpoint: str, knowledge: int) -> None:
        async with get_session() as session:
            stmt = select(ServerKnowledge).where(
                ServerKnowledge.budget_id == budget_id,
                ServerKnowledge.endpoint == endpoint,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if row:
                row.knowledge = knowledge
                row.last_synced_at = now
            else:
                session.add(ServerKnowledge(
                    budget_id=budget_id,
                    endpoint=endpoint,
                    knowledge=knowledge,
                    last_synced_at=now,
                ))
            await session.commit()

    async def upsert_entities(
        self,
        budget_id: str,
        entity_type: str,
        entities: list[YNABBaseModel],
    ) -> None:
        if not entities:
            return
        async with get_session() as session:
            for entity in entities:
                entity_data = entity.model_dump()
                entity_id = entity_data.get("id", "")

                stmt = select(CachedEntity).where(
                    CachedEntity.budget_id == budget_id,
                    CachedEntity.entity_type == entity_type,
                    CachedEntity.entity_id == entity_id,
                )
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()

                if row:
                    row.update_from_model(entity)
                else:
                    session.add(CachedEntity.from_model(budget_id, entity_type, entity))
            await session.commit()

    async def get_cached_entities(
        self,
        budget_id: str,
        entity_type: str,
        model_class: type[YNABBaseModel],
    ) -> list[YNABBaseModel]:
        async with get_session() as session:
            stmt = select(CachedEntity).where(
                CachedEntity.budget_id == budget_id,
                CachedEntity.entity_type == entity_type,
                CachedEntity.is_deleted == False,  # noqa: E712
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [row.to_model(model_class) for row in rows]

    async def has_cached_data(self, budget_id: str, endpoint: str) -> bool:
        knowledge = await self.get_knowledge(budget_id, endpoint)
        return knowledge is not None

    async def invalidate_knowledge(self, budget_id: str, endpoint: str) -> None:
        async with get_session() as session:
            stmt = select(ServerKnowledge).where(
                ServerKnowledge.budget_id == budget_id,
                ServerKnowledge.endpoint == endpoint,
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                await session.delete(row)
                await session.commit()
