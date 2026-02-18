from fastapi import APIRouter, HTTPException, status
from app.db.mongo import get_db
from app.models.admin import AdminLoginIn, TokenOut
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenOut)
async def admin_login(payload: AdminLoginIn) -> TokenOut:
    db = get_db()
    admin = await db["admins"].find_one({"email": payload.email.lower()})
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(admin["_id"]))
    return TokenOut(access_token=token)
