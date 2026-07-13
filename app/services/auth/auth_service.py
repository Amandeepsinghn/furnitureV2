from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, sign_jwt, verify_password
from app.db.schemas import Cart, User
from app.models.auth import LoginModel, LoginResponseModel, SignupModel


class AuthService:
    def __init__(self, session: Session):
        self.db = session

    async def _create_access_token(self, user: User) -> LoginResponseModel:
        access_token = await sign_jwt(
            {
                "email": user.email,
                "role": user.role,
                "id": str(user.id),
            }
        )
        return LoginResponseModel(access_token=access_token)

    async def user_signup(self, user_data: SignupModel) -> LoginResponseModel:
        existing_user = self.db.scalar(select(User.id).where(User.email == user_data.email))
        if existing_user:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            role="customer",
        )
        user.cart = Cart()

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return await self._create_access_token(user)

    async def user_login(self, user_data: LoginModel) -> LoginResponseModel:
        stmt = select(User).where(User.email == user_data.email)
        user = self.db.execute(stmt).scalar_one_or_none()

        if user is None or not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid credentials")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is inactive")

        return await self._create_access_token(user)
