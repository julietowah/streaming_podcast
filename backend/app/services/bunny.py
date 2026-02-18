import re
import uuid
import httpx
from app.core.config import settings

def _safe_filename(name: str) -> str:
    # keep letters, numbers, dot, dash, underscore
    name = name.strip().replace(" ", "-")
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)
    return name or str(uuid.uuid4())

async def bunny_upload_bytes(
    data: bytes,
    remote_path: str,
    content_type: str | None = None,
) -> str:
    remote_path = remote_path.lstrip("/")
    url = f"https://{settings.BUNNY_STORAGE_HOST}/{settings.BUNNY_STORAGE_ZONE}/{remote_path}"

    headers = {
        "AccessKey": settings.BUNNY_STORAGE_PASSWORD,
        "Content-Type": content_type or "application/octet-stream",
    }

    # 🔍 DEBUG PRINTS
    print("UPLOAD URL:", url)
    print("HOST:", settings.BUNNY_STORAGE_HOST)
    print("ZONE:", settings.BUNNY_STORAGE_ZONE)

    # 🔧 Improved timeout config
    timeout = httpx.Timeout(connect=30.0, read=300.0, write=300.0, pool=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.put(url, content=data, headers=headers)

    print("BUNNY RESPONSE STATUS:", resp.status_code)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Bunny upload failed: {resp.status_code} - {resp.text[:200]}")

    return f"{settings.BUNNY_CDN_BASE.rstrip('/')}/{remote_path}"


async def upload_audio(file_bytes: bytes, original_name: str) -> str:
    name = _safe_filename(original_name)
    key = f"episodes/{uuid.uuid4()}-{name}"
    return await bunny_upload_bytes(file_bytes, key, content_type="audio/mpeg")

async def upload_image(file_bytes: bytes, original_name: str, mime: str) -> str:
    name = _safe_filename(original_name)
    key = f"covers/{uuid.uuid4()}-{name}"
    return await bunny_upload_bytes(file_bytes, key, content_type=mime)
