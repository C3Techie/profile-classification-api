from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc
from typing import Optional, List
from datetime import datetime, timezone

from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileListResponse, ProfileData
from app.services.classification import fetch_classification_data
from app.db.session import get_db
from app.core import utils
from app.core.parser import parse_query

router = APIRouter()

@router.post("/profiles", response_model=ProfileResponse, status_code=201, response_model_exclude_none=True)
async def create_profile(profile_in: ProfileCreate, db: AsyncSession = Depends(get_db)):
    raw_name = profile_in.name
    if not raw_name or not raw_name.strip():
        raise HTTPException(status_code=400, detail="Missing or empty name")
    
    name = raw_name.strip().lower()
    
    # Check for existing profile (Idempotency)
    stmt = select(Profile).where(Profile.name == name)
    result = await db.execute(stmt)
    existing_profile = result.scalar_one_or_none()
    
    if existing_profile:
        return {
            "status": "success",
            "message": "Profile already exists",
            "data": existing_profile
        }
    
    # Fetch data from external APIs
    data = await fetch_classification_data(name)
    
    # Create new profile
    new_profile = Profile(
        id=utils.generate_uuidv7(),
        name=name,
        created_at=datetime.now(timezone.utc),
        **data
    )
    
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    
    return {"status": "success", "data": new_profile}

@router.get("/profiles/search", response_model=ProfileListResponse)
async def search_profiles(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    filters = parse_query(q)
    if filters is None:
        raise HTTPException(status_code=400, detail="Unable to interpret query")
    
    return await get_profiles_with_filters(db, page=page, limit=limit, **filters)

@router.get("/profiles/{id}", response_model=ProfileResponse, response_model_exclude_none=True)
async def get_profile(id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Profile).where(Profile.id == id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {"status": "success", "data": profile}

@router.get("/profiles", response_model=ProfileListResponse)
async def get_profiles(
    gender: Optional[str] = None,
    country_id: Optional[str] = None,
    age_group: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    min_gender_probability: Optional[float] = None,
    min_country_probability: Optional[float] = None,
    sort_by: str = Query("created_at", pattern="^(age|created_at|gender_probability)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    return await get_profiles_with_filters(
        db, 
        gender=gender, 
        country_id=country_id, 
        age_group=age_group,
        min_age=min_age,
        max_age=max_age,
        min_gender_probability=min_gender_probability,
        min_country_probability=min_country_probability,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit
    )

async def get_profiles_with_filters(
    db: AsyncSession,
    gender: Optional[str] = None,
    country_id: Optional[str] = None,
    age_group: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    min_gender_probability: Optional[float] = None,
    min_country_probability: Optional[float] = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    limit: int = 10
):
    query = select(Profile)
    
    if gender:
        query = query.where(Profile.gender == gender.lower())
    if country_id:
        query = query.where(Profile.country_id == country_id.upper())
    if age_group:
        query = query.where(Profile.age_group == age_group.lower())
    if min_age is not None:
        query = query.where(Profile.age >= min_age)
    if max_age is not None:
        query = query.where(Profile.age <= max_age)
    if min_gender_probability is not None:
        query = query.where(Profile.gender_probability >= min_gender_probability)
    if min_country_probability is not None:
        query = query.where(Profile.country_probability >= min_country_probability)
    
    # Sorting
    order_func = desc if order == "desc" else asc
    query = query.order_by(order_func(getattr(Profile, sort_by)))
    
    # Total count (for pagination)
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Pagination
    query = query.offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": profiles
    }

@router.delete("/profiles/{id}", status_code=204)
async def delete_profile(id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Profile).where(Profile.id == id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    await db.delete(profile)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
