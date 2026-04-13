import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers.onet import router as onet_router
from .routers.users import router as users_router
from .routers.cognitive import router as cognitive_router
from .routers.recommendations import router as rec_router
from .routers.skills import router as skills_router
from .routers.auth import router as auth_router
from .routers.industries import router as industries_router

app = FastAPI(title="CogniHire API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(industries_router)
app.include_router(users_router, prefix="/api")
app.include_router(onet_router, prefix="/api")
app.include_router(cognitive_router)
app.include_router(rec_router)
app.include_router(skills_router)

@app.get("/health")
def health():
    return {"status": "ok"}

# Serve static HTML frontend - MUST be last
_static = Path(__file__).resolve().parents[2] / "web" / "static"
if _static.exists():
    app.mount("/", StaticFiles(directory=str(_static), html=True), name="static")
