import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.routers import analytics, rewards, transactions


logger = logging.getLogger("tracearnly")

app = FastAPI(
    title="TracEarnly API",
    version="1.0.0",
)


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(
    request: Request,
    exc: ValidationError,
):
    """
    FastAPI 0.111 doesn't automatically turn a pydantic.ValidationError
    raised while constructing a Depends()-injected model into a clean 422.

    This normalizes it to match FastAPI's usual request-validation error
    shape.
    """

    errors = exc.errors(
        include_url=False,
        include_context=False,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": jsonable_encoder(errors),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    """
    Ensures unhandled exceptions return a JSON 500 response through
    FastAPI's exception handling instead of producing a response that
    appears to the browser as a CORS failure.
    """

    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(transactions.router)
app.include_router(rewards.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {"status": "ok"}