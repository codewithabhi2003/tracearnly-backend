import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.transaction import (
    PaginationMeta,
    TransactionListResponse,
    TransactionQuery,
    TransactionResponse,
)
from app.services.transaction_service import (
    get_transaction_by_id,
    get_transactions,
)

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"],
)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    params: TransactionQuery = Depends(),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await get_transactions(db, params)

    total_pages = math.ceil(total / params.limit) if total else 0

    return TransactionListResponse(
        data=[TransactionResponse.model_validate(r) for r in rows],
        pagination=PaginationMeta(
            page=params.page,
            limit=params.limit,
            total=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        ),
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    txn = await get_transaction_by_id(db, transaction_id)

    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return txn