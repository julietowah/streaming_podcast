from fastapi import FastAPI
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.episodes import router as episodes_router

from fastapi.middleware.cors import CORSMiddleware




app = FastAPI(title="Podcast API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.0.180:3000/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(episodes_router)
