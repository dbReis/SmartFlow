"""Checks that the database fixtures give every test a clean, real PostgreSQL."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from smartflow.models import Comment, Feedback


async def count_feedback(session_maker) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).select_from(Feedback))


async def test_each_test_starts_with_an_empty_database(session_maker):
    async with session_maker.begin() as session:
        session.add(Feedback(rating=4))

    assert await count_feedback(session_maker) == 1


async def test_rows_from_other_tests_are_gone(session_maker):
    # Same insert as the test above: still exactly one row, not two.
    async with session_maker.begin() as session:
        session.add(Feedback(rating=4))

    assert await count_feedback(session_maker) == 1


async def test_database_enforces_constraints(session_maker):
    # A comment on a feedback that doesn't exist: rejected by the foreign key.
    with pytest.raises(IntegrityError):
        async with session_maker.begin() as session:
            session.add(Comment(feedback_id=999, comment="orphan"))
