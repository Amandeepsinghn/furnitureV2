from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps.database import get_db
from app.models.auth import LoginModel, LoginResponseModel, SignupModel
from app.services.auth.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(session=db)


@router.post("/signup", response_model=LoginResponseModel, status_code=201)
async def signup(
    user_data: SignupModel,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponseModel:
    return await service.user_signup(user_data)


@router.post("/login", response_model=LoginResponseModel)
async def login(
    user_data: LoginModel,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponseModel:
    return await service.user_login(user_data)
