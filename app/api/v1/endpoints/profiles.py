from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, List

from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileListResponse, ProfileData
from app.services.classification import fetch_classification_data
from app.db.session import get_db
from app.core import utils

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
        created_at=utils.get_utc_now(),
        **data
    )
    
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    
    return {"status": "success", "data": new_profile}

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
    db: AsyncSession = Depends(get_db)
):
    query = select(Profile)
    
    if gender:
        query = query.where(Profile.gender == gender.lower())
    if country_id:
        query = query.where(Profile.country_id == country_id.upper())
    if age_group:
        query = query.where(Profile.age_group == age_group.lower())
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    return {
        "status": "success",
        "count": len(profiles),
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
