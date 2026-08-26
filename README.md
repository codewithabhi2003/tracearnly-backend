# TracEarnly Backend

The backend API for **TracEarnly**, a spending tracker and rewards platform.

TracEarnly provides transaction management, spending analytics, coin-based rewards, and reward redemption through a FastAPI and PostgreSQL backend.

## Features

- Transaction management
- Transaction search
- Transaction filtering
- Server-side pagination
- Transaction sorting
- Transaction details
- Spending analytics
- Category-based spending breakdown
- Monthly spending trends
- Dashboard summary statistics
- Coin earning system
- Rewards catalogue
- Reward redemption
- Redemption history
- Atomic reward redemption
- PostgreSQL database
- Asynchronous database operations
- Request validation
- Automated backend tests
- API documentation with Swagger and ReDoc

## Tech Stack

- Python
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- asyncpg
- Pydantic
- Pydantic Settings
- Uvicorn
- pytest
- pytest-asyncio

## Project Structure

```text
backend/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── main.py
│   ├── __init__.py
│   │
│   ├── models/
│   │   ├── redemption.py
│   │   ├── reward.py
│   │   ├── transaction.py
│   │   ├── user.py
│   │   └── __init__.py
│   │
│   ├── routers/
│   │   ├── analytics.py
│   │   ├── rewards.py
│   │   ├── transactions.py
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   ├── analytics.py
│   │   ├── redemption.py
│   │   ├── reward.py
│   │   ├── transaction.py
│   │   └── __init__.py
│   │
│   ├── services/
│   │   ├── analytics_service.py
│   │   ├── reward_service.py
│   │   ├── transaction_service.py
│   │   └── __init__.py
│   │
│   └── utils/
│       ├── timestamp_parser.py
│       └── __init__.py
│
├── scripts/
│   └── seed.py
│
├── tests/
│   ├── conftest.py
│   ├── test_rewards.py
│   ├── test_transactions.py
│   └── __init__.py
│
├── transactions_DA.json
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

## Architecture

The backend follows a layered architecture:

```text
Client
   │
   ▼
FastAPI Routers
   │
   ▼
Pydantic Schemas
   │
   ▼
Service Layer
   │
   ▼
SQLAlchemy Models
   │
   ▼
PostgreSQL
```

### Routers

Handle HTTP requests and responses.

```text
app/routers/
├── transactions.py
├── rewards.py
└── analytics.py
```

### Services

Contain application and business logic.

```text
app/services/
├── transaction_service.py
├── reward_service.py
└── analytics_service.py
```

### Models

Define the database entities.

```text
app/models/
├── user.py
├── transaction.py
├── reward.py
└── redemption.py
```

### Schemas

Define API request and response structures using Pydantic.

```text
app/schemas/
├── transaction.py
├── reward.py
├── redemption.py
└── analytics.py
```

## API Endpoints

### Health

`GET /health`

Example response:

```json
{
  "status": "ok"
}
```

### Transactions

#### List Transactions

`GET /api/transactions`

Supported query parameters:

- `page`
- `limit`
- `search`
- `category`
- `status`
- `date_from`
- `date_to`
- `amount_min`
- `amount_max`
- `sort_by`
- `sort_order`

Example:

`GET /api/transactions?page=1&limit=25`

Example with filters:

`GET /api/transactions?search=Amazon&category=Shopping&status=SUCCESS`

Example with amount range:

`GET /api/transactions?amount_min=500&amount_max=5000`

Example with sorting:

`GET /api/transactions?sort_by=amount&sort_order=desc`

#### Transaction Details

`GET /api/transactions/{transaction_id}`

Returns the details of a specific transaction.

If the transaction does not exist:

`404 Not Found`

#### Pagination

Transaction responses include pagination metadata:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 25,
    "total": 10000,
    "total_pages": 400,
    "has_next": true,
    "has_prev": false
  }
}
```

### Analytics

#### Category Breakdown

`GET /api/analytics/categories`

Returns spending totals grouped by category.

Example:

```json
[
  {
    "category": "Shopping",
    "total": "125000.00",
    "count": 250
  }
]
```

#### Monthly Trend

`GET /api/analytics/monthly`

Returns spending totals grouped by month.

#### Summary

`GET /api/analytics/summary`

Provides summary information used by the dashboard and analytics pages.

The summary includes:

- Total spending
- Transaction count
- Successful transaction count
- Failed transaction count
- Pending transaction count
- Coin balance
- Total coins earned
- Top category
- Top merchant

### Rewards

#### Reward Catalogue

`GET /api/rewards`

Returns the available rewards.

Example:

```json
[
  {
    "id": 1,
    "name": "Amazon ₹100 Voucher",
    "description": "Redeemable on Amazon.in",
    "coin_cost": 500,
    "is_active": true
  }
]
```

#### Coin Balance

`GET /api/rewards/balance`

Example response:

```json
{
  "balance": 602945
}
```

#### Redemption History

`GET /api/rewards/redemptions`

Returns previous reward redemptions.

#### Redeem Reward

`POST /api/rewards/redeem`

Request:

```json
{
  "reward_id": 2
}
```

Example successful response:

```json
{
  "success": true,
  "reward_name": "Swiggy ₹100 Voucher",
  "coins_spent": 300,
  "new_balance": 602645,
  "redeemed_at": "2026-08-26T10:30:00"
}
```

#### Reward Redemption Rules

Before a reward is redeemed, the backend validates:

- The reward exists.
- The reward is active.
- The user has enough coins.
- The balance is deducted.
- The redemption is recorded.

If the reward does not exist:

`404 Not Found`

If the user does not have enough coins:

`400 Bad Request`

The balance is not modified when a redemption fails.

#### Concurrent Redemption Protection

Reward redemption uses a database row lock to prevent race conditions when multiple redemption requests are processed simultaneously.

This ensures that the same coins cannot be spent twice.

For example, if the balance is exactly 300 coins and two requests simultaneously attempt to redeem a 300-coin reward:

- Request 1 → `SUCCESS`
- Request 2 → `INSUFFICIENT BALANCE`

The final balance becomes **0 coins**.

## Coin System

Coins are earned from successful transactions.

The current earning rule is:

**1 coin for every ₹100 spent**

Examples:

- ₹100 → 1 coin
- ₹250 → 2 coins
- ₹500 → 5 coins
- ₹1,000 → 10 coins

Only successful transactions contribute coins.

Failed and pending transactions do not earn coins.

## Database

TracEarnly uses PostgreSQL with asynchronous SQLAlchemy.

Main database entities:

- User
- Transaction
- Reward
- Redemption

The application uses SQLAlchemy models for database interaction and Pydantic schemas for API validation and serialization.

## Environment Variables

Create a `.env` file inside the backend directory.

Example:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ENVIRONMENT=development
```

### Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `CORS_ORIGINS` | Allowed frontend origins |
| `ENVIRONMENT` | Application environment |

For production, configure the appropriate frontend URL in `CORS_ORIGINS`.

Do not commit `.env` to source control.

## Local Development

### Requirements

Make sure the following are installed:

- Python 3.11+
- PostgreSQL
- pip

### 1. Clone the repository

```bash
git clone <repository-url>
cd tracearnly-project/backend
```

### 2. Create a virtual environment

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file with the following:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tracearnly
CORS_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

### 5. Prepare the database

Create the PostgreSQL database:

```sql
CREATE DATABASE tracearnly;
```

### 6. Seed the database

Run:

```bash
python -m scripts.seed
```

The seed process loads the transaction dataset and creates the required reward and demo data.

### 7. Start the API

```bash
uvicorn app.main:app --reload
```

The backend will run at `http://localhost:8000`.

## API Documentation

FastAPI provides interactive API documentation automatically.

### Swagger UI

`http://localhost:8000/docs`

### ReDoc

`http://localhost:8000/redoc`

These interfaces can be used to inspect and test the available API endpoints.

## Testing

The backend includes automated tests for transactions and rewards.

Run the complete test suite:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_transactions.py
pytest tests/test_rewards.py
```

The test suite covers:

- Transaction listing
- Pagination response structure
- Invalid transaction filters
- Invalid sorting parameters
- Amount range validation
- Missing transaction handling
- Reward catalogue
- Successful redemption
- Insufficient balance
- Invalid reward handling
- Failed redemption balance protection
- Concurrent redemption protection

## Production

The application can be deployed as a Python web service.

Production start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required production environment variables:

- `DATABASE_URL`
- `CORS_ORIGINS`
- `ENVIRONMENT`

The backend is designed to work with a separately deployed frontend through the configured CORS origins.

### Backend URL

- Production API: `https://tracearnly-backend.onrender.com`
- API documentation: `https://tracearnly-backend.onrender.com/docs`
- Health check: `https://tracearnly-backend.onrender.com/health`

## Data Seeding

The project includes the `transactions_DA.json` dataset and the `scripts/seed.py` seed script. The seed process handles importing transaction records into PostgreSQL and preparing the application data required by the rewards and analytics systems.

## Error Handling

The API returns appropriate HTTP status codes for common errors.

Examples:

- `200 OK`
- `400 Bad Request`
- `404 Not Found`
- `422 Unprocessable Entity`
- `500 Internal Server Error`

Invalid request parameters are validated before reaching the service layer.

Unhandled server errors are logged by the application while returning a consistent API response.

## CORS

The backend supports configurable CORS origins through:

```
CORS_ORIGINS=http://localhost:3000
```

Multiple origins can be configured as a comma-separated list:

```
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

For production, use the deployed frontend origin.

## Application Flow

### Transaction Flow

```text
Frontend
   ↓
GET /api/transactions
   ↓
Transaction Router
   ↓
Transaction Service
   ↓
SQLAlchemy
   ↓
PostgreSQL
   ↓
Transaction Response
```

### Reward Redemption Flow

```text
Frontend
   ↓
POST /api/rewards/redeem
   ↓
Rewards Router
   ↓
Reward Service
   ↓
Validate Reward
   ↓
Lock User Balance
   ↓
Validate Coins
   ↓
Deduct Coins
   ↓
Create Redemption
   ↓
Commit Transaction
   ↓
Response
```

## Health Check

The backend exposes a lightweight health endpoint:

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

This can be used by deployment platforms and monitoring systems to verify that the API is running.

## License

No license has been specified for this project yet. Add a `LICENSE` file (for example, MIT or Apache 2.0) if this repository will be made public or open-sourced.
