import asyncio
import os
from datetime import datetime, timezone

from app.core.security import hash_password
from app.db.mongo import get_db, get_client


EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123").strip()


async def main():
    db = get_db()
    existing = await db["admins"].find_one({"email": EMAIL})
    if existing:
        print(f"Admin already exists: {EMAIL}")
        return

    now = datetime.now(timezone.utc)
    doc = {
        "email": EMAIL,
        "password_hash": hash_password(PASSWORD),
        "created_at": now,
        "updated_at": now,
    }
    await db["admins"].insert_one(doc)
    print(f"Admin created: {EMAIL}")

    client = get_client()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
