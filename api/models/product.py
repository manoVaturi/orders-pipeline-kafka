from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class ProductCreate(BaseModel):
    sku: str
    name: str
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)


class ProductResponse(ProductCreate):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId | None = Field(alias="_id", default=None)
    created_at: datetime | None = None


class ProductModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId | None = Field(alias="_id", default=None)
    sku: str
    name: str
    price: float = Field(gt=0)
