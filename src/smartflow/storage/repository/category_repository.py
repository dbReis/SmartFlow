from collections.abc import Sequence

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.category import Category

log = structlog.get_logger(__name__)


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_category(self, name: str, description: str | None) -> Category:
        log.debug("creating_category")
        category = Category(name=name, description=description)
        self.session.add(category)

        await self.session.flush()
        log.debug("category_inserted", category_id=category.id)
        return category

    async def get_category(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)

    async def list_categories(self) -> Sequence[Category]:
        result = await self.session.scalars(select(Category).order_by(Category.name))
        return result.all()
