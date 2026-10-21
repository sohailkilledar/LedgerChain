"""Repository foundation.

Layering: API route -> service -> repository -> Session -> PostgreSQL.

- Repositories only read and write rows. They ``flush`` (so generated ids and constraint
  errors surface immediately) but never ``commit``.
- Services hold business rules and own the transaction (``session.commit()``).
- Routes receive a request-scoped session via ``app.db.session.DbSession`` and pass it on.

Subclass with a concrete model::

    class WidgetRepository(Repository[Widget]):
        model = Widget
"""

from collections.abc import Sequence
from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)

MAX_PAGE_SIZE = 500


class Repository(Generic[ModelT]):
    model: ClassVar[type[Any]]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, entity_id: Any) -> ModelT | None:
        return self.session.get(self.model, entity_id)

    def list_page(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        offset = max(0, offset)
        statement = select(self.model).limit(limit).offset(offset)
        return self.session.scalars(statement).all()

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: ModelT) -> None:
        self.session.delete(entity)
        self.session.flush()
