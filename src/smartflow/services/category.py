import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.category import Category
from smartflow.schemas.category import CategoryCreate
from smartflow.storage.repository.category_repository import CategoryRepository

log = structlog.get_logger(__name__)


async def create_category(session: AsyncSession, data: CategoryCreate) -> Category:
    category = await CategoryRepository(session).add_category(
        name=data.name, description=data.name
    )
    log.info(
        "category_created",
        category_id=category.id,
        name=category.name,
        description=category.description,
    )

    return category
