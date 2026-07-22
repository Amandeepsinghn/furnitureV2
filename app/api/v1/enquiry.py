from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps.database import get_db
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse
from app.services.email.email_service import EmailService
from app.services.enquiry.enquiry_service import EnquiryService

router = APIRouter(prefix="/enquiries", tags=["enquiries"])


def get_email_service() -> EmailService:
    return EmailService()


def get_enquiry_service(
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> EnquiryService:
    return EnquiryService(session=db, email_service=email_service)


@router.post("", response_model=EnquiryResponse, status_code=status.HTTP_201_CREATED)
def submit_enquiry(
    payload: EnquiryCreate,
    service: EnquiryService = Depends(get_enquiry_service),
) -> EnquiryResponse:
    return service.create_enquiry(payload)
