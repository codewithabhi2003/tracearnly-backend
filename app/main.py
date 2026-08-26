from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.routers import analytics, auth, rewards, transactions

app = FastAPI(title="TracEarnly API", version="1.0.0")


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """
    FastAPI 0.111 doesn't automatically turn a pydantic.ValidationError raised
    while constructing a Depends()-injected model (e.g. cross-field validators
    on TransactionQuery, like amount_max >= amount_min) into a clean 422 — left
    alone it propagates as an unhandled 500. This normalizes it to match
    FastAPI's usual request-validation error shape.
    """
    # errors() can contain raw Python objects (e.g. a `date`) in "input", which
    # plain json.dumps can't serialize — route it through jsonable_encoder first.
    errors = exc.errors(include_url=False, include_context=False)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(errors)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(rewards.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
