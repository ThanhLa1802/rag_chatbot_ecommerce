from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProductUpdatePayload(BaseModel):
    product_id: int = Field(..., description="ID gốc của sản phẩm")
    name: str
    description: str
    category: str
    price: float

class ProductResponse(BaseModel):
    """Response model for product retrieval"""
    product_id: int
    name: str
    description: str
    category: str
    price: float
    status: str = "active"
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True