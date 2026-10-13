from unittest.mock import AsyncMock, Mock, call

import pytest

from smartflow.models import Feedback
from smartflow.schemas.feedback import FeedbackMergeCreate
from smartflow.services import feedback_service
from smartflow.services.errors import (
    CannotMergeIntoItselfError,
    FeedbackAlreadyMergedError,
    FeedbackNotFoundError,
)

SESSION = Mock(name="session")  # never used directly: the repositories are mocked


@pytest.fixture
def feedback_by_id() -> dict[int, Feedback]:
    return {
        1: Feedback(id=1, rating=2, merged_into_id=None),
        2: Feedback(id=2, rating=3, merged_into_id=None),
        3: Feedback(id=3, rating=4, merged_into_id=2),
    }


@pytest.fixture
def repositories(monkeypatch, feedback_by_id):
    calls = Mock()

    feedback_repo = Mock()
    feedback_repo.get_feedback = AsyncMock(side_effect=feedback_by_id.get)
    calls.attach_mock(AsyncMock(), "repoint_merged")
    calls.attach_mock(AsyncMock(), "merge")
    feedback_repo.repoint_merged = calls.repoint_merged
    feedback_repo.merge = calls.merge

    comment_repo = Mock()
    calls.attach_mock(AsyncMock(return_value=2), "move_comments")
    comment_repo.move_comments = calls.move_comments

    monkeypatch.setattr(feedback_service, "FeedbackRepository", lambda _: feedback_repo)
    monkeypatch.setattr(feedback_service, "CommentRepository", lambda _: comment_repo)
    return calls


async def merge(source_id: int, target_id: int):
    return await feedback_service.merge(
        SESSION, source_id, FeedbackMergeCreate(target_id=target_id)
    )


async def test_merge_moves_comments_repoints_then_marks_source(
    repositories, feedback_by_id
):
    result = await merge(1, 2)

    assert result is feedback_by_id[2]  # the target, which now holds everything
    assert repositories.mock_calls == [
        call.move_comments(1, 2),
        call.repoint_merged(1, 2),
        call.merge(feedback_by_id[1], target_id=2),
    ]


async def test_merge_into_itself_is_rejected_before_any_change(repositories):
    with pytest.raises(CannotMergeIntoItselfError):
        await merge(1, 1)

    assert repositories.mock_calls == []


@pytest.mark.parametrize(("source", "target"), [(999, 2), (1, 999)])
async def test_merge_with_unknown_feedback_is_rejected(repositories, source, target):
    with pytest.raises(FeedbackNotFoundError) as exc_info:
        await merge(source, target)

    assert exc_info.value.feedback_id == 999
    assert repositories.mock_calls == []


@pytest.mark.parametrize(("source", "target"), [(3, 1), (1, 3)])
async def test_merge_involving_already_merged_feedback_is_rejected(
    repositories, source, target
):
    with pytest.raises(FeedbackAlreadyMergedError) as exc_info:
        await merge(source, target)

    assert exc_info.value.feedback_id == 3
    assert repositories.mock_calls == []
