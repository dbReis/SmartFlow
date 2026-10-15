"""Business rules for categories."""

from collections.abc import Sequence

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.category import Category
from smartflow.schemas.category import CategoryCreate
from smartflow.storage.repository.category_repository import CategoryRepository

log = structlog.get_logger(__name__)


async def create_category(session: AsyncSession, data: CategoryCreate) -> Category:
    """Create a category.

    Args:
        session: The request's session, inside a transaction the caller commits.
        data: The validated request body.

    Returns:
        The new category, with its id assigned.
    """
    category = await CategoryRepository(session).add_category(
        name=data.name, description=data.description
    )
    log.info(
        "category_created",
        category_id=category.id,
        name=category.name,
        description=category.description,
    )

    return category


async def list_categories(session: AsyncSession) -> Sequence[Category]:
    """Return every category, sorted by name."""
    return await CategoryRepository(session).list_categories()
