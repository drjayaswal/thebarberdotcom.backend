import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.database.db import init_db
from app.core.config import settings
from app.core.tasks import register_tasks

from app.api.v1.auth import router as auth_router
from app.api.v1.seat import router as seats_router
from app.api.v1.saved import router as saved_router
from app.api.v1.upload import router as upload_router
from app.api.v1.barber import router as barbers_router
from app.api.v1.review import router as reviews_router
from app.api.v1.booking import router as bookings_router

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

env = settings()
scheduler = BackgroundScheduler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    register_tasks(scheduler)
    scheduler.start()
    logger.info("scheduler started")
    
    yield
    
    logger.info("scheduler stopped")
    scheduler.shutdown()


app = FastAPI(
    title=os.getenv("PROJECT_NAME", "TheBarberDotCom API"),
    lifespan=lifespan,
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[env.NEXT_PUBLIC_APP_URL, "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(seats_router, prefix="/seats")
app.include_router(saved_router, prefix="/saved")
app.include_router(upload_router, prefix="/upload")
app.include_router(reviews_router, prefix="/reviews")
app.include_router(barbers_router, prefix="/barbers")
app.include_router(bookings_router, prefix="/bookings")

@app.get("/")
async def root():
    return {
        "message": "thebarberdotcom running",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": os.getenv("TZ", "IST")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=True)