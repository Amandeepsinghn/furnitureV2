from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.schemas import Enquiry, Product
from app.schemas.enquiry import EnquiryCreate, EnquiryResponse
from app.services.email.email_service import EmailService


class EnquiryService:
    def __init__(self, session: Session, email_service: EmailService | None = None):
        self.db = session
        self.email_service = email_service or EmailService()

    def create_enquiry(self, payload: EnquiryCreate) -> EnquiryResponse:
        product = self.db.get(Product, payload.product_id)
        if product is None or not product.is_active:
            raise HTTPException(status_code=404, detail="Product not found")

        enquiry = Enquiry(
            product_id=payload.product_id,
            product_slug=payload.product_slug,
            product_name=payload.product_name,
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            preferred_contact=payload.preferred_contact,
            message=payload.message,
        )
        self.db.add(enquiry)
        self.db.commit()
        self.db.refresh(enquiry)

        self.email_service.send_enquiry_notification(
            product_id=payload.product_id,
            product_slug=payload.product_slug,
            product_name=payload.product_name,
            full_name=payload.full_name,
            phone=payload.phone,
            email=payload.email,
            preferred_contact=payload.preferred_contact,
            message=payload.message,
        )

        return EnquiryResponse(
            id=enquiry.id,
            created_at=enquiry.created_at,
        )
