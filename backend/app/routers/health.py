from fastapi import APIRouter
from app.db.mongo import get_db

router = APIRouter(tags=["health"])

@router.get("/health")
async def health():
    db = get_db()
    # Simple ping: list collections (fast & safe)
    await db.list_collection_names()
    return {"status": "ok"}
