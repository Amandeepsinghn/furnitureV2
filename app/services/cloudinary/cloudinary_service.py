import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE_MB = 10


def configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_secret_key,
        secure=True,
    )


class CloudinaryService:
    def __init__(self) -> None:
        configure_cloudinary()

    async def upload_image(
        self,
        file: UploadFile,
        *,
        folder: str = "furniture/products",
    ) -> dict[str, str]:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type: {file.content_type}",
            )

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded image file is empty")

        max_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit",
            )

        try:
            result = cloudinary.uploader.upload(
                contents,
                folder=folder,
                resource_type="image",
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Failed to upload image to Cloudinary") from exc

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    async def upload_images(
        self,
        files: list[UploadFile],
        *,
        folder: str = "furniture/products",
    ) -> list[dict[str, str]]:
        uploads: list[dict[str, str]] = []
        for file in files:
            uploads.append(await self.upload_image(file, folder=folder))
        return uploads

    def delete_image(self, public_id: str) -> None:
        try:
            cloudinary.uploader.destroy(public_id, resource_type="image")
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to delete image from Cloudinary",
            ) from exc
