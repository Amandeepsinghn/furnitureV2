from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
