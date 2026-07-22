from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EnquiryCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: int = Field(alias="productId")
    product_slug: str = Field(alias="productSlug", max_length=220)
    product_name: str = Field(alias="productName", max_length=200)
    full_name: str = Field(alias="fullName", min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=20)
    email: EmailStr
    preferred_contact: Literal["whatsapp", "phone", "email"] = Field(alias="preferredContact")
    message: str | None = Field(default=None, max_length=2000)


class EnquiryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str = "Enquiry submitted successfully"
    created_at: datetime
