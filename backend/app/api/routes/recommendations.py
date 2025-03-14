import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select
from app.models import Product, Category, User, ProductsPublic
from app.api.deps import SessionDep, CurrentUser


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/", response_model=ProductsPublic)
def get_recommendations(
        user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser,
        skip: int = 0, limit: int = 10
) -> Any:
    """
    Get product recommendations for the user.
    The algorithm fetches products from the same category or based on previous purchases.
    """

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    previous_products = session.exec(select(Product).where(Product.owner_id == user.id)).all()

    recommended_products = []
    if previous_products:
        categories = [product.category_id for product in previous_products]

        statement = (
            select(Product)
            .where(Product.category_id.in_(categories))
            .where(Product.id.not_in([product.id for product in previous_products]))
            .offset(skip)
            .limit(limit)
        )
        recommended_products = session.exec(statement).all()

    if not recommended_products:
        statement = (
            select(Product)
            .order_by(Product.rating.desc())
            .offset(skip)
            .limit(limit)
        )
        recommended_products = session.exec(statement).all()

    return ProductsPublic(data=recommended_products, count=len(recommended_products))