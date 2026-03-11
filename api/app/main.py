from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.app.db.init import init_db
from api.app.routes.auth import router as auth_router
from api.app.routes.bots import router as bots_router
from api.app.routes.health import router as health_router
from api.app.routes.runs import router as runs_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Polymarket Web API", lifespan=lifespan)

app.include_router(health_router)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(bots_router, prefix="/bots", tags=["bots"])
app.include_router(runs_router, prefix="/runs", tags=["runs"])
