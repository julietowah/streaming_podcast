from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi import UploadFile, File, Form
from bson import ObjectId

from app.db.mongo import get_db
from app.models.episode import EpisodeUpdateIn, EpisodeOut, EpisodeCreateJSON
from app.core.security import require_admin_token
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

MAX_AUDIO_BYTES = 4 * 1024 * 1024        # 4 MB
MAX_COVER_BYTES = 1 * 1024 * 1024        # 1 MB

def _fmt_mb(n: int) -> str:
    return f"{n / (1024 * 1024):.1f}MB"

async def _read_with_limit(file: UploadFile, limit_bytes: int, label: str) -> bytes:
    """
    Read upload into memory but enforce size limit.
    Note: if the platform rejects large bodies (Vercel), you may never reach this code.
    """
    # Prefer content-length if provided by client (not always present)
    if file.size is not None and file.size > limit_bytes:  # UploadFile may not have .size in some setups
        raise HTTPException(
            status_code=413,
            detail=f"{label} is too large. Max allowed is {_fmt_mb(limit_bytes)}.",
        )

    data = await file.read()
    if len(data) > limit_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{label} is too large ({_fmt_mb(len(data))}). Max allowed is {_fmt_mb(limit_bytes)}.",
        )
    return data

@router.post("/admin/episodes", response_model=EpisodeOut, status_code=status.HTTP_201_CREATED)
async def admin_create_episode(
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("General"),
    published: bool = Form(True),

    audio: UploadFile | None = File(None),
    cover: UploadFile | None = File(None),

    # Optional fallbacks
    audio_url: str | None = Form(None),
    thumbnail_url: str | None = Form(None),

    admin_id: str = Depends(require_admin_token),
):
    db = get_db()

    resolved_audio_url = (audio_url or "").strip()
    resolved_thumbnail_url = (thumbnail_url or "").strip()

    # Require either file or URL for both
    if audio is None and not resolved_audio_url:
        raise HTTPException(
            status_code=400,
            detail=f"Provide audio file or audio_url. If uploading a file, keep it under {_fmt_mb(MAX_AUDIO_BYTES)} on Vercel."
        )
    if cover is None and not resolved_thumbnail_url:
        raise HTTPException(
            status_code=400,
            detail=f"Provide cover file or thumbnail_url. If uploading a file, keep it under {_fmt_mb(MAX_COVER_BYTES)} on Vercel."
        )

    # Upload audio file -> Bunny
    if audio is not None:
        if audio.content_type not in ("audio/mpeg", "audio/mp3", "audio/x-mpeg", "audio/*"):
            raise HTTPException(status_code=400, detail=f"Audio must be mp3/mpeg. Got {audio.content_type}")

        try:
            audio_bytes = await _read_with_limit(audio, MAX_AUDIO_BYTES, "Audio file")
            resolved_audio_url = await upload_audio(audio_bytes, audio.filename or "audio.mp3")
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Storage timeout on audio upload")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Audio upload failed: {exc}")

    # Upload cover -> Bunny
    if cover is not None:
        if cover.content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(status_code=400, detail=f"Cover must be jpg/png/webp. Got {cover.content_type}")

        try:
            cover_bytes = await _read_with_limit(cover, MAX_COVER_BYTES, "Cover image")
            resolved_thumbnail_url = await upload_image(
                cover_bytes,
                cover.filename or "cover.jpg",
                cover.content_type or "application/octet-stream",
            )
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Storage timeout on cover upload")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Cover upload failed: {exc}")

    now = datetime.now(timezone.utc)

    doc = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip() or "General",
        "published": bool(published),
        "audio_url": resolved_audio_url,
        "thumbnail_url": resolved_thumbnail_url,
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
