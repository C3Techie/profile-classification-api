# Profile Classification API - Stage 2: Intelligence Query Engine

A professional, industry-standard FastAPI-based system upgraded for advanced demographic intelligence. It features complex filtering, sorting, pagination, and a rule-based natural language search engine.

## Features
- **Advanced Filtering**: Slice data by gender, age ranges, age groups, country, and probability thresholds.
- **Sorting & Pagination**: Full support for paginated results with configurable limits and sorting by various metrics.
- **Intelligence Query Engine (NLQ)**: A rule-based parser that interprets English sentences like "young males from Nigeria" and maps them to database filters.
- **Data Seeding**: Automated ingestion of 2026 profiles from JSON data with idempotency checks.
- **UUID v7**: Uses the latest UUID standard for high-performance indexing and uniqueness.
- **Vercel Optimized**: Ready for deployment to Vercel Serverless Functions.

## Intelligence Query Engine (NLQ)

The `GET /api/profiles/search` endpoint implements a logic-driven parser for plain English queries.

### How the Parser Works
The parser uses a rule-based regex engine to translate human intentions into database filters:

1. **Gender Extraction** (word-boundary safe):
   - `male` or `males` → `gender=male`
   - `female` or `females` → `gender=female`
   - Both present (e.g., `male and female`) → no gender filter applied

2. **Age Range Mapping**:
   - `young` → `min_age=16, max_age=24`
   - `above X` / `over X` / `older than X` → `min_age=X`
   - `below X` / `under X` / `younger than X` → `max_age=X`

3. **Age Group Matching** (word-boundary safe):
   - `child` or `children` → `age_group=child`
   - `teenager` or `teenagers` → `age_group=teenager`
   - `adult` or `adults` → `age_group=adult`
   - `senior` or `seniors` → `age_group=senior`

4. **Geographic Intent**:
   - `from [country name]` → maps to ISO 3166-1 alpha-2 code
   - Country names are matched longest-first to avoid partial matches (e.g., `south africa` before `africa`)
   - Supports 80+ country names including common aliases (e.g., `uk`, `usa`, `ivory coast`)

### Supported Query Examples
| Query | Resulting Filters |
|---|---|
| `young males` | `gender=male, min_age=16, max_age=24` |
| `females above 30` | `gender=female, min_age=30` |
| `people from angola` | `country_id=AO` |
| `adult males from kenya` | `gender=male, age_group=adult, country_id=KE` |
| `male and female teenagers above 17` | `age_group=teenager, min_age=17` |
| `seniors from germany` | `age_group=senior, country_id=DE` |
| `young females from south africa` | `gender=female, min_age=16, max_age=24, country_id=ZA` |

### Limitations
- **Stateless**: No context memory between requests.
- **Keyword-dependent**: Only recognizes exact listed keywords. Novel synonyms like "grown-up" won't be mapped.
- **Single country**: Only the first matched country is used; multi-country queries are not supported.
- **No boolean OR logic**: Queries like "males from Nigeria or Kenya" are not supported.
- **No negation**: Queries like "males not from Nigeria" are not supported.
- **No name search**: The parser operates on demographic filters only, not profile names.

## API Endpoints

### 1. Create Profile
`POST /api/profiles`
- **Body**: `{ "name": "ella" }`
- **Description**: Classifies a name and returns the profile.

### 2. Search Profiles (NLQ)
`GET /api/profiles/search?q=young males from Nigeria`
- **Description**: Returns profiles matching the interpreted natural language intent.

### 3. List Profiles (Advanced)
`GET /api/profiles`
- **Params**: `gender`, `country_id`, `age_group`, `min_age`, `max_age`, `sort_by`, `order`, `page`, `limit`.
- **Description**: Full filtering and pagination support.

## Installation & Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Initialize and Seed Database:
   ```bash
   # Seeds 2026 profiles from seed_profiles.json
   set PYTHONPATH=. && python app/db/seed.py
   ```
3. Run Server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Running Tests
```bash
set PYTHONPATH=. && pytest tests/test_profiles.py
```

## Deployment (Vercel)
The project is pre-configured with `vercel.json`. Simply connect your GitHub repository and set `DATABASE_URL` in your environment variables.
