import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Product, ProductCreate, ProductPublic, ProductsPublic, ProductUpdate, Message, Category

router = APIRouter(prefix="/products", tags=["products"])


# Get all products
@router.get("/", response_model=ProductsPublic)
def read_products(
        session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve products.
    """
    # If the user is an admin, retrieve all products
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Product)
        count = session.exec(count_statement).one()
        statement = select(Product).offset(skip).limit(limit)
        products = session.exec(statement).all()
    else:
        # Otherwise, retrieve products belonging to the user (if applicable)
        count_statement = (
            select(func.count())
            .select_from(Product)
            .where(Product.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Product)
            .where(Product.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        )
        products = session.exec(statement).all()

    return ProductsPublic(data=products, count=count)


# Get a specific product by ID
@router.get("/{id}", response_model=ProductPublic)
def read_product(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get product by ID.
    """
    product = session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not current_user.is_superuser and (product.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return product


# Create a new product
@router.post("/", response_model=ProductPublic)
def create_product(
        *, session: SessionDep, current_user: CurrentUser, product_in: ProductCreate
) -> Any:
    """
    Create a new product.
    """
    # Ensure the category exists
    category = session.get(Category, product_in.category_id)
    if not category:
        raise HTTPException(status_code=400, detail="Category not found")

    # Create the new product
    product = Product.model_validate(product_in, update={"owner_id": current_user.id})
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


# Update a product
@router.put("/{id}", response_model=ProductPublic)
def update_product(
        *,
        session: SessionDep,
        current_user: CurrentUser,
        id: uuid.UUID,
        product_in: ProductUpdate,
) -> Any:
    """
    Update a product.
    """
    product = session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not current_user.is_superuser and (product.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    # Update the product with new data
    update_dict = product_in.model_dump(exclude_unset=True)
    product.sqlmodel_update(update_dict)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


# Delete a product
@router.delete("/{id}")
def delete_product(
        session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a product.
    """
    product = session.get(Product, id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if not current_user.is_superuser and (product.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    session.delete(product)
    session.commit()
    return Message(message="Product deleted successfully")
