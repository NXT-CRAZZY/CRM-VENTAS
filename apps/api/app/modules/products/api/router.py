from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.products.application.use_cases import ProductService
from app.modules.products.repository import SqlProductRepository
from app.modules.products.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ProductCreate,
    ProductFilters,
    ProductRead,
    ProductUpdate,
)
from app.modules.rbac.domain.permissions import P
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(tags=["Productos"])
CanRead = Depends(require(P.PRODUCTS_READ))
CanManage = Depends(require(P.PRODUCTS_MANAGE))


def _service(db: DbSession, audit: Audit) -> ProductService:
    return ProductService(SqlProductRepository(db), audit)


Service = Annotated[ProductService, Depends(_service)]


@router.get("/product-categories", response_model=list[CategoryRead], dependencies=[CanRead])
def list_categories(service: Service) -> list[CategoryRead]:
    return service.list_categories()


@router.post(
    "/product-categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED, dependencies=[CanManage]
)
def create_category(data: CategoryCreate, service: Service) -> CategoryRead:
    return service.create_category(data)


@router.patch("/product-categories/{category_id}", response_model=CategoryRead, dependencies=[CanManage])
def update_category(category_id: UUID, data: CategoryUpdate, service: Service) -> CategoryRead:
    return service.update_category(category_id, data)


@router.get("/products", response_model=Page[ProductRead], dependencies=[CanRead])
def list_products(
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    q: str | None = Query(None, description="Busca por código o nombre"),
    category_id: UUID | None = None,
    product_line: str | None = None,
    status_: Literal["active", "inactive", "all"] = Query("active", alias="status"),
) -> Page[ProductRead]:
    filters = ProductFilters(q=q, category_id=category_id, product_line=product_line, status=status_)
    return service.list_products(filters, params)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED, dependencies=[CanManage])
def create_product(data: ProductCreate, service: Service) -> ProductRead:
    return service.create_product(data)


@router.get("/products/{product_id}", response_model=ProductRead, dependencies=[CanRead])
def get_product(product_id: UUID, service: Service) -> ProductRead:
    return service.get_product(product_id)


@router.patch("/products/{product_id}", response_model=ProductRead, dependencies=[CanManage])
def update_product(product_id: UUID, data: ProductUpdate, service: Service) -> ProductRead:
    return service.update_product(product_id, data)
