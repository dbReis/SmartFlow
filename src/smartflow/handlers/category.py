"""``/api/category``: anyone can list categories, only PMs can create them."""

from smartflow.handlers.pm_base_handler import PMHandler
from smartflow.schemas.category import CategoryCreate, CategoryListOut, CategoryOut
from smartflow.services.category import create_category, list_categories


class CategoryHandler(PMHandler):
    """List (public) and create (PM only) categories."""

    public_methods = ("GET",)

    async def get(self):
        """Return every category, sorted by name."""
        async with self.session_maker() as session:
            categories = await list_categories(session)

        items = [CategoryOut.model_validate(category) for category in categories]
        self.finish(CategoryListOut(items=items).model_dump(mode="json"))

    async def post(self):
        """Create a category and answer 201 with it.

        Raises:
            HTTPError: 400/422 if the body is invalid; 401/503 from PMHandler.
        """
        data = self.parse_body(CategoryCreate)
        async with self.session_maker.begin() as session:
            category = await create_category(session, data)

        self.set_status(201)
        self.set_header("Location", "/api/category")
        self.finish(CategoryOut.model_validate(category).model_dump(mode="json"))
