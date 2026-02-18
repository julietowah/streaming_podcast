from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId

from app.db.mongo import get_db
from app.models.episode import EpisodeCreateIn, EpisodeUpdateIn, EpisodeOut
from app.core.security import require_admin_token
from fastapi import UploadFile, File, Form
from app.services.bunny import upload_audio, upload_image


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
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("General"),
    published: bool = Form(True),
    audio: UploadFile = File(...),
    cover: UploadFile = File(...),
    admin_id: str = Depends(require_admin_token),
):
    db = get_db()

    # Validate file types quickly
    if audio.content_type not in ("audio/mpeg", "audio/mp3", "audio/x-mpeg"):
        raise HTTPException(status_code=400, detail=f"Audio must be mp3/mpeg. Got {audio.content_type}")

    if cover.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail=f"Cover must be jpg/png/webp. Got {cover.content_type}")

    audio_bytes = await audio.read()
    cover_bytes = await cover.read()

    # Upload to Bunny with explicit upstream error mapping
    try:
        audio_url = await upload_audio(audio_bytes, audio.filename or "audio.mp3")
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Storage upload timed out while uploading audio.",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed while uploading audio: {exc.__class__.__name__}.",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage rejected audio upload: {str(exc)}",
        )

    try:
        thumb_url = await upload_image(cover_bytes, cover.filename or "cover.jpg", cover.content_type)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Storage upload timed out while uploading cover image.",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed while uploading cover image: {exc.__class__.__name__}.",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage rejected cover upload: {str(exc)}",
        )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    doc = {
        "title": title,
        "description": description,
        "category": category,
        "published": published,
        "audio_url": audio_url,
        "thumbnail_url": thumb_url,
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
