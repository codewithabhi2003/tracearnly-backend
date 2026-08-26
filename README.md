# TracEarnly Backend

The backend API for **TracEarnly**, a personal spending tracker and rewards platform.

TracEarnly provides transaction management, spending analytics, coin-based rewards, and reward redemption through a FastAPI and PostgreSQL backend.

## Features

- Transaction management
- Transaction search and filtering
- Pagination and sorting
- Spending analytics
- Monthly spending trends
- Category-based spending breakdown
- Dashboard summary statistics
- Coin earning system
- Rewards catalogue
- Reward redemption
- Redemption history
- PostgreSQL database
- Async database operations
- API validation
- Automated backend tests

## Tech Stack

- Python
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- asyncpg
- Pydantic
- Uvicorn
- pytest

## Project Structure

```text
backend/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── main.py
│   │
│   ├── models/
│   │   ├── redemption.py
│   │   ├── reward.py
│   │   ├── transaction.py
│   │   └── user.py
│   │
│   ├── routers/
│   │   ├── analytics.py
│   │   ├── rewards.py
│   │   └── transactions.py
│   │
│   ├── schemas/
│   │   ├── analytics.py
│   │   ├── redemption.py
│   │   ├── reward.py
│   │   └── transaction.py
│   │
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── reward_service.py
│   │   └── transaction_service.py
│   │
│   └── utils/
│       └── timestamp_parser.py
│
├── scripts/
│   └── seed.py
│
├── tests/
│   ├── conftest.py
│   ├── test_rewards.py
│   └── test_transactions.py
│
├── transactions_DA.json
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.md
