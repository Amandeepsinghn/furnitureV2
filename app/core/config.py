from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440
    cloudinary_api_key: str = Field(validation_alias="API_Key")
    cloudinary_secret_key: str = Field(validation_alias="API_Secret")
    cloudinary_cloud_name: str = Field(validation_alias="Cloud_Name")
    google_app_password: str | None = Field(default=None, validation_alias="GOOGLE_APP_PASSWORD")
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_sender_email: str = Field(
        default="amandeepsingh.kaillay@gmail.com",
        validation_alias="SMTP_SENDER_EMAIL",
    )
    cart_notification_email: str = Field(
        default="amandeepsingh.kaillay@gmail.com",
        validation_alias="CART_NOTIFICATION_EMAIL",
    )


settings = Settings()
