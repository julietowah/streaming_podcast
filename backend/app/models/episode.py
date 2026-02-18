from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EpisodeIn(BaseModel):
    title: str
    description: str = ""
    category: str = "General"
    audio_url: str
    thumbnail_url: str
    published: bool = True


class EpisodeCreateIn(BaseModel):
    title: str
    description: str = ""
    category: str = "General"
    audio_url: str
    thumbnail_url: str
    published: bool = True

class EpisodeUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published: Optional[bool] = None

class EpisodeOut(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    category: str
    audio_url: str
    thumbnail_url: str
    published: bool
    created_at: datetime
    updated_at: datetime