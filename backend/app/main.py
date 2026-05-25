import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.care_plans.routes import router as care_plans_router
from app.database import init_db
from app.orders.routes import router as orders_router

load_dotenv()
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize local development database tables when the FastAPI app starts."""
    # Learning-project shortcut. In production, use Alembic migrations instead of
    # creating tables automatically at application startup.
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

# The browser app runs on port 3000 during local development and calls this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Keep main.py focused on application wiring; domain endpoints live in routers.
app.include_router(orders_router)
app.include_router(care_plans_router)
