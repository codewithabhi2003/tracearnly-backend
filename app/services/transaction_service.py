from datetime import timedelta

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionQuery


async def get_transactions(
    db: AsyncSession, params: TransactionQuery
) -> tuple[list[Transaction], int]:
    query = select(Transaction)

    if params.search:
        # pg_trgm-backed ILIKE — see idx_txn_merchant_trgm in the model.
        query = query.where(Transaction.merchant.ilike(f"%{params.search}%"))
    if params.category:
        query = query.where(Transaction.category == params.category)
    if params.status:
        query = query.where(Transaction.status == params.status)
    if params.date_from:
        query = query.where(Transaction.timestamp >= params.date_from)
    if params.date_to:
        query = query.where(Transaction.timestamp < params.date_to + timedelta(days=1))
    if params.amount_min is not None:
        query = query.where(Transaction.amount >= params.amount_min)
    if params.amount_max is not None:
        query = query.where(Transaction.amount <= params.amount_max)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Sort by mapped column attribute only — never string-format into order_by,
    # which would open a SQL injection vector. sort_by is also constrained by a
    # Pydantic regex, so this is defense in depth.
    sort_col = Transaction.timestamp if params.sort_by == "timestamp" else Transaction.amount
    sort_expr = asc(sort_col) if params.sort_order == "asc" else desc(sort_col)
    query = query.order_by(sort_expr, Transaction.id.asc())

    offset = (params.page - 1) * params.limit
    query = query.offset(offset).limit(params.limit)

    result = await db.execute(query)
    rows = list(result.scalars().all())
    return rows, int(total or 0)


async def get_transaction_by_id(db: AsyncSession, transaction_id: int) -> Transaction | None:
    return await db.get(Transaction, transaction_id)
