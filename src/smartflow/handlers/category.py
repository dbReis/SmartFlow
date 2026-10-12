from smartflow.handlers.pm_base_handler import PMHandler
from smartflow.schemas.category import CategoryCreate, CategoryOut
from smartflow.services.category import create_category


class CategoryHandler(PMHandler):
    async def post(self):
        data = self.parse_body(CategoryCreate)
        async with self.session_maker.begin() as session:
            category = await create_category(session, data)

        self.set_status(201)
        self.set_header("Location", "/api/category")
        self.finish(CategoryOut.model_validate(category).model_dump(mode="json"))

    def add_feedback(self):
        pass
