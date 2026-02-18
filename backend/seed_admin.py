import asyncio
import os

# import your app's DB init + models + hash function
from app.db.core.database import init_db  # adjust import to your project
from app.models.user_models import User   # adjust import
from app.core.security import hash_password  # adjust import

EMAIL = "admin@example.com"
PASSWORD = "admin123"
NAME = "Admin"

async def main():
    await init_db()

    existing = await User.find_one(User.email == EMAIL)
    if existing:
        print("Admin already exists:", EMAIL)
        return

    admin = User(
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        name=NAME,
        role="admin",
    )
    await admin.insert()
    print("✅ Admin created:", EMAIL)

if __name__ == "__main__":
    # Ensure your MONGO_URI env var is set before running
    asyncio.run(main())
