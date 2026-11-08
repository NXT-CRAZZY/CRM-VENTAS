from uuid import UUID

from app.core.errors import ConflictError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder, diff
from app.modules.products.infrastructure.models import Product, ProductCategory
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ProductCreate,
    ProductFilters,
    ProductRead,
    ProductUpdate,
)
from app.shared.pagination import Page, PageParams
from app.shared.text import slug_code


def _snapshot(p: Product) -> dict:
    return {
        "code": p.code,
        "name": p.name,
        "description": p.description,
        "category": p.category.name if p.category else None,
        "kind": p.kind,
        "billing_period": p.billing_period,
        "list_price": p.list_price,
        "is_active": p.is_active,
        "legacy_code": p.legacy_code,
    }


class ProductService:
    def __init__(self, repo: ProductRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

    # ---- Categorías ----
    def list_categories(self) -> list[CategoryRead]:
        out = []
        for category, count in self.repo.list_categories():
            item = CategoryRead.model_validate(category)
            item.product_count = count
            out.append(item)
        return out

    def _category(self, category_id: UUID) -> ProductCategory:
        category = self.repo.get_category(category_id)
        if category is None:
            raise NotFoundError("La categoría no existe.")
        return category

    def create_category(self, data: CategoryCreate) -> CategoryRead:
        if self.repo.get_category_by_name(data.name):
            raise ConflictError("Ya existe una categoría con ese nombre.", code="CATEGORY_NAME_TAKEN")
        code = slug_code(data.name)
        if self.repo.get_category_by_code(code):
            code = f"{code[:34]}_{self.repo.next_category_order()}"
        category = ProductCategory(
            code=code,
            name=data.name.strip(),
            product_line=data.product_line.strip(),
            sort_order=self.repo.next_category_order(),
            is_active=True,
        )
        self.repo.add_category(category)
        if self.audit:
            self.audit.record("product_category.created", "product_category", category.public_id, label=category.name)
        return CategoryRead.model_validate(category)

    def update_category(self, category_id: UUID, data: CategoryUpdate) -> CategoryRead:
        category = self._category(category_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if "name" in changes:
            other = self.repo.get_category_by_name(changes["name"])
            if other and other.id != category.id:
                raise ConflictError("Ya existe una categoría con ese nombre.", code="CATEGORY_NAME_TAKEN")
        before = {k: getattr(category, k) for k in changes}
        for k, v in changes.items():
            setattr(category, k, v.strip() if isinstance(v, str) else v)
        self.repo.add_category(category)
        if self.audit and changes:
            self.audit.record(
                "product_category.updated",
                "product_category",
                category.public_id,
                label=category.name,
                before=before,
                after=changes,
            )
        return CategoryRead.model_validate(category)

    # ---- Productos ----
    def list_products(self, filters: ProductFilters, params: PageParams) -> Page[ProductRead]:
        items, total = self.repo.list_products(filters, params)
        return Page[ProductRead](
            items=[ProductRead.model_validate(p) for p in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def _product(self, product_id: UUID) -> Product:
        product = self.repo.get_product(product_id)
        if product is None:
            raise NotFoundError("El producto no existe.")
        return product

    def get_product(self, product_id: UUID) -> ProductRead:
        return ProductRead.model_validate(self._product(product_id))

    def create_product(self, data: ProductCreate) -> ProductRead:
        code = data.code.strip().upper()
        if self.repo.get_product_by_code(code):
            raise ConflictError("Ya existe un producto con ese código.", code="PRODUCT_CODE_TAKEN")
        product = Product(
            code=code,
            name=data.name.strip(),
            description=data.description,
            category=self._category(data.category_id),
            kind=data.kind.value,
            billing_period=data.billing_period.value,
            list_price=data.list_price,
            legacy_code=data.legacy_code,
            is_active=True,
        )
        self.repo.add_product(product)
        if self.audit:
            self.audit.record(
                "product.created", "product", product.public_id, label=product.name, after=_snapshot(product)
            )
        return ProductRead.model_validate(product)

    def update_product(self, product_id: UUID, data: ProductUpdate) -> ProductRead:
        product = self._product(product_id)
        before = _snapshot(product)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("code"):
            code = changes["code"].strip().upper()
            other = self.repo.get_product_by_code(code)
            if other and other.id != product.id:
                raise ConflictError("Ya existe un producto con ese código.", code="PRODUCT_CODE_TAKEN")
            product.code = code
        if changes.get("category_id"):
            product.category = self._category(changes["category_id"])
        for field in ("name", "description", "kind", "billing_period", "list_price", "legacy_code", "is_active"):
            if field in changes and (changes[field] is not None or field in ("description", "legacy_code")):
                value = changes[field]
                if field == "name":
                    value = value.strip()
                if field in ("kind", "billing_period"):
                    value = value.value if hasattr(value, "value") else value
                setattr(product, field, value)
        self.repo.add_product(product)
        if self.audit:
            b, a = diff(before, _snapshot(product))
            if a:
                action = "product.price_changed" if "list_price" in a else "product.updated"
                self.audit.record(action, "product", product.public_id, label=product.name, before=b, after=a)
        return ProductRead.model_validate(product)
