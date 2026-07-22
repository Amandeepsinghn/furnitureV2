"""Seed default furniture categories."""

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.schemas import Category

CATEGORIES = [
    {"name": "Sofas", "slug": "sofas", "description": "Sofas and couches", "sort_order": 1},
    {"name": "Tables", "slug": "tables", "description": "Dining and coffee tables", "sort_order": 2},
    {"name": "Chairs", "slug": "chairs", "description": "Chairs and seating", "sort_order": 3},
    {"name": "Beds", "slug": "beds", "description": "Beds and bedroom furniture", "sort_order": 4},
    {"name": "Dining Tables", "slug": "dining-tables", "description": "Dining tables for home and office", "sort_order": 5},
]


def seed_categories() -> None:
    db = SessionLocal()
    try:
        for data in CATEGORIES:
            existing = db.scalar(select(Category).where(Category.slug == data["slug"]))
            if existing:
                print(f"Skipped (exists): {data['name']}")
                continue

            db.add(Category(**data, is_active=True))
            print(f"Created: {data['name']}")

        db.commit()
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()
