import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from smartflow.models.notation import Notation
from smartflow.schemas.notation import NotationCreate
from smartflow.services.errors import CommentNotFoundError
from smartflow.storage.repository.comment_repository import CommentRepository
from smartflow.storage.repository.notation_repository import NotationRepository

log = structlog.get_logger(__name__)


async def create_notation(
    session: AsyncSession, comment_id: int, data: NotationCreate
) -> Notation:
    if await CommentRepository(session).get_comment(comment_id=comment_id) is None:
        log.info("notation_comment_not_found", comment_id=comment_id)
        raise CommentNotFoundError

    notation = await NotationRepository(session).add_notation(
        comment_id=comment_id, notation=data.notation
    )
    log.info("notation_created", notation_id=notation.id, comment_id=comment_id)
    return notation
