import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from smartflow.models import Feedback, Notation


def create_table_sql(model) -> str:
    sql = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
    return " ".join(sql.split())  # one line, single spaces: easier to search


@pytest.fixture(scope="module")
def feedback_sql() -> str:
    return create_table_sql(Feedback)


def test_rating_is_limited_to_1_to_5(feedback_sql):
    assert "CHECK (rating IN (1, 2, 3, 4, 5))" in feedback_sql


def test_status_values_are_quoted_text(feedback_sql):
    # Without quotes PostgreSQL would read them as column names. SQL keywords
    # are case-insensitive, so compare in lower case.
    expected = "check (status in ('open', 'closed_backlog', 'closed_solved', 'closed_rejected'))"
    assert expected in feedback_sql.lower()


def test_new_feedback_is_open_by_default(feedback_sql):
    assert "status VARCHAR(20) DEFAULT 'open' NOT NULL" in feedback_sql


def test_deleting_a_category_or_merge_target_keeps_the_feedback(feedback_sql):
    assert "REFERENCES category (id) ON DELETE SET NULL" in feedback_sql
    assert "REFERENCES feedback (id) ON DELETE SET NULL" in feedback_sql


def test_notation_is_limited_to_minus_one_zero_and_one():
    assert "CHECK (notation IN (-1, 0, 1))" in create_table_sql(Notation)
