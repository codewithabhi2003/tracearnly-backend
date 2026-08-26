from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


async def get_category_breakdown(db: AsyncSession):
    # Pure SQL aggregation. Refunds (amount <= 0) excluded — see ASSUMPTIONS.md.
    result = await db.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.amount > 0)
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )
    return result.all()


async def get_monthly_trend(db: AsyncSession):
    # Reuse the SAME expression object for SELECT/GROUP BY/ORDER BY. Calling
    # func.to_char(...) three separate times (as an earlier version did)
    # gives each call its own bound parameter for the "YYYY-MM" format
    # string ($1, $4, $5, etc.) — even though they're textually identical,
    # Postgres treats them as different expressions and rejects the query
    # with "column transactions.timestamp must appear in the GROUP BY
    # clause". Building the expression once and reusing it compiles to the
    # same bound parameter everywhere, which Postgres accepts.
    month_expr = func.to_char(Transaction.timestamp, "YYYY-MM").label("month")
    result = await db.execute(
        select(
            month_expr,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.amount > 0)
        .group_by(month_expr)
        .order_by(month_expr)
    )
    return result.all()


async def get_summary(db: AsyncSession, coin_balance: int) -> dict:
    total_spending = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.amount > 0)
    )
    transaction_count = await db.scalar(select(func.count(Transaction.id)))
    successful_count = await db.scalar(
        select(func.count(Transaction.id)).where(Transaction.status == "SUCCESS")
    )
    failed_count = await db.scalar(
        select(func.count(Transaction.id)).where(Transaction.status == "FAILED")
    )
    pending_count = await db.scalar(
        select(func.count(Transaction.id)).where(Transaction.status == "PENDING")
    )
    total_coins_earned = await db.scalar(
        select(func.coalesce(func.sum(Transaction.coins_earned), 0)).where(
            Transaction.status == "SUCCESS"
        )
    )

    top_category_row = await db.execute(
        select(Transaction.category, func.sum(Transaction.amount).label("total"))
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.amount > 0)
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(1)
    )
    top_category = top_category_row.first()

    top_merchant_row = await db.execute(
        select(Transaction.merchant, func.sum(Transaction.amount).label("total"))
        .where(Transaction.status == "SUCCESS")
        .where(Transaction.amount > 0)
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(1)
    )
    top_merchant = top_merchant_row.first()

    return {
        "total_spending": total_spending or 0,
        "transaction_count": transaction_count or 0,
        "successful_count": successful_count or 0,
        "failed_count": failed_count or 0,
        "pending_count": pending_count or 0,
        "coin_balance": coin_balance,
        "total_coins_earned": int(total_coins_earned or 0),
        "top_category": top_category[0] if top_category else None,
        "top_merchant": top_merchant[0] if top_merchant else None,
    }