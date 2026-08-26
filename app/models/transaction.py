from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Original TXN id from the source dataset. Unique, but see ASSUMPTIONS.md re: 40
    # colliding IDs in the raw data — duplicates are suffixed to preserve all rows.
    external_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # null = seeded/demo data
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    merchant: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="Other")
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # SUCCESS / FAILED / PENDING
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_txn_status_timestamp", "status", "timestamp"),
        Index("idx_txn_category_timestamp", "category", "timestamp"),
        Index("idx_txn_amount", "amount"),
        Index(
            "idx_txn_merchant_trgm",
            text("merchant gin_trgm_ops"),
            postgresql_using="gin",
        ),
    )
