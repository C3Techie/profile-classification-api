# Profile Classification API

A professional, industry-standard FastAPI-based system that classifies profiles by integrating with external APIs (Genderize, Agify, and Nationalize), stores data in a database, and provides management endpoints.

## Features
- **Profile Classification**: Automatically determines gender, age, and nationality using external data.
- **Industry Standard Layout**: Modular structure with separated concerns (API, Core, DB, Models, Schemas, Services).
- **Data Persistence**: Configured for PostgreSQL (Vercel/Production) with SQLite support for local development.
- **Idempotency**: Prevents duplicate records for the same name, returning existing data instead.
- **UUID v7**: Uses the latest UUID standard for all record identifiers.
- **Vercel Optimized**: Pre-configured for seamless deployment to Vercel Serverless Functions.

## Directory Structure
```text
profile-classification-api/
├── app/
│   ├── api/                # API Routers (v1)
│   ├── core/               # Configuration and Utilities
│   ├── db/                 # Database Session and Base
│   ├── models/             # SQLAlchemy Models
│   ├── schemas/            # Pydantic Schemas
│   ├── services/           # External API Logic
│   └── main.py             # Application Entry Point
├── tests/                  # Automated Test Suite
├── requirements.txt        # Dependency List
├── vercel.json           # Vercel Configuration
└── README.md
```

## API Endpoints

### 1. Create Profile
`POST /api/profiles`
- **Body**: `{ "name": "ella" }`
- **Description**: Classifies a name and returns the profile. If name exists, returns the existing record.

### 2. Get Single Profile
`GET /api/profiles/{id}`
- **Description**: Returns detailed data for a specific profile ID.

### 3. Get All Profiles
`GET /api/profiles`
- **Query Params**: `gender`, `country_id`, `age_group` (all optional and case-insensitive).
- **Description**: Returns a list of profiles with filtering options.

### 4. Delete Profile
`DELETE /api/profiles/{id}`
- **Description**: Removes a profile record.

## Setup & Local Development

### Prerequisites
- Python 3.12+

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

### Running Tests
To run the automated test suite:
```bash
# Windows
$env:PYTHONPATH="."; pytest -v tests/test_profiles.py

# Linux / MacOS
PYTHONPATH=. pytest -v tests/test_profiles.py
```

## Deployment (Vercel)
1. Link your repository to a new Vercel project.
2. Add your **PostgreSQL** connection string as `DATABASE_URL` in the environment variables.
3. Deploy! The `vercel.json` and entry points are already configured.
