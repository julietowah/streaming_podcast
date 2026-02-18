import asyncio
from app.db.mongo import get_db
from app.core.security import hash_password

EMAIL = "admin@example.com"
PASSWORD = "admin123"  # change this

async def main():
    db = get_db()
    admins = db["admins"]
    existing = await admins.find_one({"email": EMAIL.lower()})
    if existing:
        print("Admin already exists:", EMAIL)
        return

    await admins.insert_one({
        "email": EMAIL.lower(),
        "password_hash": hash_password(PASSWORD),
        "role": "admin",
    })
    print("Created admin:", EMAIL)

if __name__ == "__main__":
    asyncio.run(main())
