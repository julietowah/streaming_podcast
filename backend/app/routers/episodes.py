from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId

from app.db.mongo import get_db
from app.models.episode import EpisodeCreateIn, EpisodeUpdateIn, EpisodeOut
from app.core.security import require_admin_token


router = APIRouter(tags=["episodes"])

def oid(id_: str) -> ObjectId:
    try:
        return ObjectId(id_)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

# -----------------------
# Public endpoints (Mobile)
# -----------------------

@router.get("/episodes", response_model=List[EpisodeOut])
async def list_published_episodes():
    db = get_db()
    cursor = db["episodes"].find({"published": True}).sort("created_at", -1)
    items = await cursor.to_list(length=200)
    for x in items:
        x["_id"] = str(x["_id"])
    return items

@router.get("/episodes/{episode_id}", response_model=EpisodeOut)
async def get_published_episode(episode_id: str):
    db = get_db()
    doc = await db["episodes"].find_one({"_id": oid(episode_id), "published": True})
    if not doc:
        raise HTTPException(status_code=404, detail="Episode not found")
    doc["_id"] = str(doc["_id"])
    return doc

# -----------------------
# Admin endpoints (Next.js Admin)
# -----------------------

@router.get("/admin/episodes", response_model=List[EpisodeOut])
async def admin_list_all_episodes(admin_id: str = Depends(require_admin_token)):
    db = get_db()
    cursor = db["episodes"].find({}).sort("created_at", -1)
    items = await cursor.to_list(length=500)
    for x in items:
        x["_id"] = str(x["_id"])
    return items

@router.post("/admin/episodes", response_model=EpisodeOut, status_code=status.HTTP_201_CREATED)
async def admin_create_episode(
    payload: EpisodeCreateIn,
    admin_id: str = Depends(require_admin_token),
):
    db = get_db()
    now = datetime.now(timezone.utc)

    doc = {
        "title": payload.title,
        "description": payload.description,
        "category": payload.category,
        "published": payload.published,
        "audio_url": payload.audio_url,
        "thumbnail_url": payload.thumbnail_url,
        "created_at": now,
        "updated_at": now,
        "created_by": admin_id,
    }
    res = await db["episodes"].insert_one(doc)
    saved = await db["episodes"].find_one({"_id": res.inserted_id})
    saved["_id"] = str(saved["_id"])
    return saved


@router.patch("/admin/episodes/{episode_id}", response_model=EpisodeOut)
async def admin_update_episode(
    episode_id: str,
    payload: EpisodeUpdateIn,
    admin_id: str = Depends(require_admin_token),
):
    db = get_db()
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")

    update["updated_at"] = datetime.now(timezone.utc)

    res = await db["episodes"].find_one_and_update(
        {"_id": oid(episode_id)},
        {"$set": update},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Episode not found")

    res["_id"] = str(res["_id"])
    return res

@router.delete("/admin/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_episode(episode_id: str, admin_id: str = Depends(require_admin_token)):
    db = get_db()
    res = await db["episodes"].delete_one({"_id": oid(episode_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Episode not found")
    return None
