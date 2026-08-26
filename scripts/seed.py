"""
TracEarnly seed script.

Run with:
    python -m scripts.seed

Responsibilities:
- Enables pg_trgm before creating the merchant GIN index.
- Creates all database tables through SQLAlchemy metadata.
- Seeds the reward catalogue.
- Loads and normalizes transactions_DA.json.
- Handles all supported timestamp formats through timestamp_parser.
- Handles malformed/missing categories and statuses.
- Keeps negative amounts as refunds.
- Calculates reward coins for successful positive transactions.
- Handles duplicate external transaction IDs.
- Inserts transactions in batches.
- Safe to re-run.

Database:
    PostgreSQL + asyncpg
"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# ---------------------------------------------------------------------------
# Make the backend directory importable when running:
# python -m scripts.seed
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.models.reward import Reward  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402
from app.utils.timestamp_parser import parse_timestamp  # noqa: E402


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATASET_PATH = (
    Path(__file__).resolve().parent.parent / "transactions_DA.json"
)

COIN_RATE = 100
COIN_CAP = 500
BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Valid dataset values
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "SUCCESS",
    "FAILED",
    "PENDING",
}

VALID_CATEGORIES = {
    "Travel",
    "Shopping",
    "Utilities",
    "Food & Dining",
    "Health",
    "Education",
    "Entertainment",
    "Groceries",
    "Fuel",
    "Insurance",
    "Other",
}


# ---------------------------------------------------------------------------
# Reward catalogue
# ---------------------------------------------------------------------------

REWARDS = [
    {
        "name": "Amazon ₹100 Voucher",
        "description": "Redeemable on Amazon.in",
        "coin_cost": 500,
    },
    {
        "name": "Flipkart ₹100 Voucher",
        "description": "Redeemable on Flipkart",
        "coin_cost": 500,
    },
    {
        "name": "Swiggy ₹100 Voucher",
        "description": "Redeemable on Swiggy",
        "coin_cost": 300,
    },
    {
        "name": "Zomato ₹100 Voucher",
        "description": "Redeemable on Zomato",
        "coin_cost": 300,
    },
    {
        "name": "₹50 Cashback",
        "description": "Direct cashback to your account",
        "coin_cost": 200,
    },
    {
        "name": "Movie Voucher ₹150",
        "description": "BookMyShow movie ticket voucher",
        "coin_cost": 600,
    },
]


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def normalize_status(raw: str) -> str:
    """
    Normalize transaction status.

    Examples:
        SUCCESS -> SUCCESS
        success -> SUCCESS
        FAILED  -> FAILED
        PENDING -> PENDING

    Unknown values are treated as PENDING.
    """
    normalized = str(raw).strip().upper()

    if normalized in VALID_STATUSES:
        return normalized

    return "PENDING"


def normalize_category(raw) -> str:
    """
    Normalize transaction categories.

    Missing values and:
        None
        NONE
        NULL
        ""

    are mapped to Other.
    """

    if raw is None:
        return "Other"

    cleaned = str(raw).strip()

    if not cleaned:
        return "Other"

    if cleaned.upper() in {"NONE", "NULL"}:
        return "Other"

    if cleaned not in VALID_CATEGORIES:
        return "Other"

    return cleaned


def parse_amount(raw) -> float:
    """
    Convert transaction amount to float.

    Supports:
        1234.50
        "1234.50"
        "1,234.50"

    Negative values are intentionally preserved because they represent
    refunds/reversals in the provided dataset.
    """

    if isinstance(raw, (int, float)):
        return float(raw)

    try:
        return float(
            str(raw)
            .replace(",", "")
            .strip()
        )
    except (ValueError, TypeError):
        return 0.0


def calculate_coins(amount: float, status: str) -> int:
    """
    Calculate reward coins.

    Rules:
        - 1 coin per ₹100
        - SUCCESS transactions only
        - Negative/refund transactions earn 0
        - FAILED transactions earn 0
        - PENDING transactions earn 0
        - Maximum 500 coins per transaction
    """

    if status != "SUCCESS":
        return 0

    if amount <= 0:
        return 0

    coins = int(amount // COIN_RATE)

    return min(coins, COIN_CAP)


# ---------------------------------------------------------------------------
# Duplicate external IDs
# ---------------------------------------------------------------------------

def dedupe_external_ids(rows: list[dict]) -> list[dict]:
    """
    Make external IDs unique.

    The source dataset contains duplicate external IDs representing
    different transactions.

    Because external_id is UNIQUE in PostgreSQL, repeated IDs receive
    a deterministic suffix instead of silently dropping transactions.

    Example:
        TXN123
        TXN123

    becomes:

        TXN123
        TXN123-dup2
    """

    seen: Counter[str] = Counter()

    for row in rows:
        external_id = row["external_id"]

        seen[external_id] += 1

        if seen[external_id] > 1:
            row["external_id"] = (
                f"{external_id}-dup{seen[external_id]}"
            )

    return rows


# ---------------------------------------------------------------------------
# Enable PostgreSQL extension
# ---------------------------------------------------------------------------

async def enable_pg_trgm() -> None:
    """
    Enable PostgreSQL pg_trgm extension.

    IMPORTANT:
    This must happen BEFORE Base.metadata.create_all()
    because the Transaction model contains:

        merchant gin_trgm_ops

    which requires pg_trgm.
    """

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE EXTENSION IF NOT EXISTS pg_trgm"
            )
        )

    print("✓ PostgreSQL pg_trgm extension enabled")


# ---------------------------------------------------------------------------
# Create database schema
# ---------------------------------------------------------------------------

async def create_schema() -> None:
    """
    Create all SQLAlchemy tables and indexes.
    """

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all
        )

    print("✓ Database schema created")


# ---------------------------------------------------------------------------
# Seed rewards
# ---------------------------------------------------------------------------

async def seed_rewards() -> None:
    """
    Seed the reward catalogue.

    Reward names are checked manually because the Reward model does not
    currently have a UNIQUE constraint on name.
    """

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            Reward.__table__.select()
        )

        existing_rewards = result.first()

        if existing_rewards:
            print("✓ Rewards already seeded, skipping")

            return

        rewards = [
            Reward(**reward)
            for reward in REWARDS
        ]

        db.add_all(rewards)

        await db.commit()

        print(
            f"✓ Seeded {len(rewards)} rewards"
        )


# ---------------------------------------------------------------------------
# Load and normalize transaction dataset
# ---------------------------------------------------------------------------

def load_transactions() -> tuple[list[dict], int]:
    """
    Load transactions_DA.json and normalize all rows.

    Returns:
        normalized transactions
        skipped row count
    """

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    print(
        f"✓ Loaded {len(raw_data):,} raw transactions"
    )

    normalized: list[dict] = []
    skipped = 0

    for index, row in enumerate(raw_data):

        try:
            timestamp = parse_timestamp(
                row["timestamp"]
            )

            status = normalize_status(
                row.get("status", "")
            )

            amount = round(
                parse_amount(
                    row.get("amount", 0)
                ),
                2,
            )

            category = normalize_category(
                row.get("category")
            )

            coins = calculate_coins(
                amount,
                status,
            )

            external_id = str(
                row["id"]
            ).strip()

            merchant = str(
                row.get(
                    "merchant",
                    "Unknown",
                )
            ).strip()[:200]

            currency = str(
                row.get(
                    "currency",
                    "INR",
                )
            ).strip()[:10]

            payment_method = str(
                row.get(
                    "payment_method",
                    "Unknown",
                )
            ).strip()[:50]

            normalized.append(
                {
                    "external_id": external_id,
                    "timestamp": timestamp,
                    "merchant": merchant,
                    "category": category,
                    "amount": amount,
                    "currency": currency,
                    "status": status,
                    "payment_method": payment_method,
                    "coins_earned": coins,
                }
            )

        except Exception as exc:
            skipped += 1

            print(
                f"⚠ Skipping row {index} "
                f"(id={row.get('id')}) "
                f"— parse error: {exc}"
            )

    normalized = dedupe_external_ids(
        normalized
    )

    return normalized, skipped


# ---------------------------------------------------------------------------
# Insert transactions
# ---------------------------------------------------------------------------

async def insert_transactions(
    transactions: list[dict],
) -> None:
    """
    Insert transactions in batches.

    Uses PostgreSQL ON CONFLICT DO NOTHING so that the seed script
    can safely be executed multiple times.
    """

    if not transactions:
        print("⚠ No transactions to insert")

        return

    async with AsyncSessionLocal() as db:

        total = len(transactions)

        for start in range(
            0,
            total,
            BATCH_SIZE,
        ):
            batch = transactions[
                start:start + BATCH_SIZE
            ]

            statement = (
                pg_insert(Transaction)
                .values(batch)
                .on_conflict_do_nothing(
                    index_elements=[
                        "external_id"
                    ]
                )
            )

            await db.execute(statement)

            batch_number = (
                start // BATCH_SIZE
            ) + 1

            total_batches = (
                (total + BATCH_SIZE - 1)
                // BATCH_SIZE
            )

            print(
                f"  Inserted batch "
                f"{batch_number}/{total_batches}"
            )

        await db.commit()

    print(
        f"✓ Processed {total:,} transactions"
    )


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

async def seed() -> None:
    """
    Complete seed workflow.

    Order is important:

        1. Enable pg_trgm
        2. Create schema/indexes
        3. Seed rewards
        4. Load dataset
        5. Normalize data
        6. Insert transactions
    """

    print()
    print("=" * 60)
    print("TracEarnly Database Seed")
    print("=" * 60)
    print()

    # IMPORTANT:
    # pg_trgm MUST exist before SQLAlchemy creates the GIN index.
    await enable_pg_trgm()

    # Create tables and indexes.
    await create_schema()

    # Seed rewards.
    await seed_rewards()

    # Load and normalize transactions.
    normalized, skipped = load_transactions()

    print(
        f"✓ Normalized {len(normalized):,} transactions"
    )

    if skipped:
        print(
            f"⚠ Skipped {skipped:,} invalid rows"
        )

    # Insert transactions.
    await insert_transactions(
        normalized
    )

    print()
    print("=" * 60)
    print("✓ Seed complete")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(seed())