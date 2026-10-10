from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    is_available: bool = True
    dietary_tags: list[str] = Field(default_factory=list)
    @field_validator("name", "category")
    @classmethod
    def nonblank(cls, v: str) -> str:
        v = v.strip()
        if not v: raise ValueError("Field cannot be blank")
        return v

class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    is_available: bool | None = None
    dietary_tags: list[str] | None = None

class MenuItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    description: str
    price: Decimal
    is_available: bool
    dietary_tags: list[str]
    created_at: datetime
    updated_at: datetime
