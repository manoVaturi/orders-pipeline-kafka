from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: str
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    price_at_purchase: float


class OrderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId | None = Field(alias="_id", default=None)
    user_id: str
    items: list[OrderItem]
    total_amount: float
    status: str
    created_at: datetime | None = None
