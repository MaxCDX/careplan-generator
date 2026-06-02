import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.care_plans.routes import router as care_plans_router
from app.database import init_db
from app.exceptions import BaseAppException
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


@app.exception_handler(BaseAppException)
async def app_exception_handler(request, exc: BaseAppException):
    """Return a consistent envelope for expected application errors."""
    log_func = logging.error if exc.status_code >= 500 else logging.warning
    log_func("Application error handled: code=%s message=%s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request, exc):
    """Return Bad Request for malformed client input in this learning project."""
    logging.info("Request validation error handled: error_count=%s", len(exc.errors()))
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Invalid request input.",
            "detail": jsonable_encoder(exc.errors()),
        },
    )

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
