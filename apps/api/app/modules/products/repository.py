from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.products.infrastructure.models import Product, ProductCategory
from app.modules.products.schemas import ProductFilters
from app.shared.pagination import PageParams, paginate


class ProductRepository(Protocol):
    def list_categories(self) -> list[tuple[ProductCategory, int]]: ...
    def get_category(self, public_id: UUID) -> ProductCategory | None: ...
    def get_category_by_name(self, name: str) -> ProductCategory | None: ...
    def get_category_by_code(self, code: str) -> ProductCategory | None: ...
    def next_category_order(self) -> int: ...
    def add_category(self, category: ProductCategory) -> None: ...
    def list_products(self, filters: ProductFilters, params: PageParams) -> tuple[list[Product], int]: ...
    def get_product(self, public_id: UUID) -> Product | None: ...
    def get_product_by_code(self, code: str) -> Product | None: ...
    def add_product(self, product: Product) -> None: ...


class SqlProductRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def list_categories(self) -> list[tuple[ProductCategory, int]]:
        count = select(func.count(Product.id)).where(Product.category_id == ProductCategory.id).scalar_subquery()
        stmt = select(ProductCategory, count).order_by(ProductCategory.sort_order, ProductCategory.name)
        return [(c, n) for c, n in self.s.execute(stmt)]

    def get_category(self, public_id: UUID) -> ProductCategory | None:
        return self.s.scalar(select(ProductCategory).where(ProductCategory.public_id == public_id))

    def get_category_by_name(self, name: str) -> ProductCategory | None:
        return self.s.scalar(select(ProductCategory).where(func.lower(ProductCategory.name) == name.lower()))

    def get_category_by_code(self, code: str) -> ProductCategory | None:
        return self.s.scalar(select(ProductCategory).where(ProductCategory.code == code))

    def next_category_order(self) -> int:
        return (self.s.scalar(select(func.max(ProductCategory.sort_order))) or 0) + 10

    def add_category(self, category: ProductCategory) -> None:
        self.s.add(category)
        self.s.flush()

    def list_products(self, filters: ProductFilters, params: PageParams) -> tuple[list[Product], int]:
        stmt = (
            select(Product)
            .join(ProductCategory, ProductCategory.id == Product.category_id)
            .order_by(ProductCategory.sort_order, Product.code)
        )
        if filters.status == "active":
            stmt = stmt.where(Product.is_active.is_(True))
        elif filters.status == "inactive":
            stmt = stmt.where(Product.is_active.is_(False))
        if filters.category_id:
            stmt = stmt.where(ProductCategory.public_id == filters.category_id)
        if filters.product_line:
            stmt = stmt.where(ProductCategory.product_line == filters.product_line)
        if filters.q:
            like = f"%{filters.q.strip()}%"
            stmt = stmt.where(or_(Product.code.ilike(like), Product.name.ilike(like)))
        return paginate(self.s, stmt, params)

    def get_product(self, public_id: UUID) -> Product | None:
        return self.s.scalar(select(Product).where(Product.public_id == public_id))

    def get_product_by_code(self, code: str) -> Product | None:
        return self.s.scalar(select(Product).where(func.upper(Product.code) == code.upper()))

    def add_product(self, product: Product) -> None:
        self.s.add(product)
        self.s.flush()
