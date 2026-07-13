from pydantic import BaseModel, EmailStr, Field


class LoginModel(BaseModel):
    email: EmailStr
    password: str


class SignupModel(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=20)


class LoginResponseModel(BaseModel):
    access_token: str
