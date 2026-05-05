import csv
import io
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.profile import Profile
from app.core.utils import generate_uuidv7
from app.services.classification import get_age_group, get_country_name
from datetime import datetime, timezone
from fastapi import UploadFile

BATCH_SIZE = 1000

async def process_csv_ingestion(file: UploadFile, db: AsyncSession) -> Dict[str, Any]:
    """
    Process CSV ingestion with streaming and batching.
    Handles idempotency (skip duplicates) and row validation.
    """
    total_rows = 0
    inserted_count = 0
    skipped_count = 0
    reasons = {
        "duplicate_name": 0,
        "invalid_age": 0,
        "missing_fields": 0,
        "invalid_gender": 0,
        "malformed_row": 0
    }

    # Wrap the UploadFile stream in a TextIOWrapper for csv.DictReader
    # Since UploadFile.file is a file-like object (SpooledTemporaryFile)
    text_stream = io.TextIOWrapper(file.file, encoding='utf-8-sig', errors='replace')
    reader = csv.DictReader(text_stream)

    batch = []
    
    # Helper to flush batch to DB
    async def flush_batch(rows: List[Dict[str, Any]]):
        if not rows:
            return 0
        
        # Use PostgreSQL ON CONFLICT DO NOTHING for idempotency
        stmt = pg_insert(Profile).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=['name'])
        
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount # Returns number of rows actually inserted

    for row in reader:
        total_rows += 1
        
        # 1. Basic validation
        name = row.get("name", "").strip().lower()
        gender = row.get("gender", "").strip().lower()
        age_str = row.get("age", "").strip()
        country_id = row.get("country_id", "").strip().upper()

        if not all([name, gender, age_str, country_id]):
            skipped_count += 1
            reasons["missing_fields"] += 1
            continue

        try:
            age = int(age_str)
            if age < 0:
                raise ValueError()
        except ValueError:
            skipped_count += 1
            reasons["invalid_age"] += 1
            continue

        if gender not in ["male", "female"]:
            skipped_count += 1
            reasons["invalid_gender"] += 1
            continue

        # 2. Construct profile data
        profile_data = {
            "id": generate_uuidv7(),
            "name": name,
            "gender": gender,
            "gender_probability": float(row.get("gender_probability", 1.0)),
            "age": age,
            "age_group": get_age_group(age),
            "country_id": country_id,
            "country_name": get_country_name(country_id),
            "country_probability": float(row.get("country_probability", 1.0)),
            "created_at": datetime.now(timezone.utc)
        }
        
        batch.append(profile_data)

        # 3. Batch insert if limit reached
        if len(batch) >= BATCH_SIZE:
            rows_inserted = await flush_batch(batch)
            inserted_count += rows_inserted
            # Rows skipped due to conflict
            skipped_in_batch = len(batch) - rows_inserted
            skipped_count += skipped_in_batch
            reasons["duplicate_name"] += skipped_in_batch
            batch = []

    # Final flush
    if batch:
        rows_inserted = await flush_batch(batch)
        inserted_count += rows_inserted
        skipped_in_batch = len(batch) - rows_inserted
        skipped_count += skipped_in_batch
        reasons["duplicate_name"] += skipped_in_batch

    # Detach to avoid closing the underlying file if needed, 
    # though TextIOWrapper closure is usually fine.
    text_stream.detach()

    return {
        "status": "success",
        "total_rows": total_rows,
        "inserted": inserted_count,
        "skipped": skipped_count,
        "reasons": {k: v for k, v in reasons.items() if v > 0}
    }
