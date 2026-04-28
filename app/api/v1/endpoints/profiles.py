import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc

from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import (
    ProfileCreate,
    ProfileResponse,
    ProfileListResponse,
    ProfileData,
    PaginationLinks,
)
from app.services.classification import fetch_classification_data
from app.db.session import get_db
from app.core import utils
from app.core.parser import parse_query
from app.core.dependencies import get_current_user, require_admin, require_analyst, require_api_version

router = APIRouter()


# ── Shared filter helper ───────────────────────────────────────────────────────

async def _build_filtered_query(
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
):
    """Build a filtered + sorted query (without pagination)."""
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

    order_func = desc if order == "desc" else asc
    query = query.order_by(order_func(getattr(Profile, sort_by)))
    return query


def _build_links(request: Request, page: int, limit: int, total_pages: int) -> PaginationLinks:
    """Build HATEOAS-style pagination links."""
    base = request.url.path
    # Preserve existing query params except page
    params = dict(request.query_params)
    params["limit"] = str(limit)

    def make_url(p: int) -> str:
        params["page"] = str(p)
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base}?{qs}"

    return PaginationLinks(
        self=make_url(page),
        next=make_url(page + 1) if page < total_pages else None,
        prev=make_url(page - 1) if page > 1 else None,
    )


async def get_profiles_with_filters(
    db: AsyncSession,
    request: Request,
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
    limit: int = 10,
):
    query = await _build_filtered_query(
        db, gender, country_id, age_group, min_age, max_age,
        min_gender_probability, min_country_probability, sort_by, order,
    )

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    total_pages = max(1, (total + limit - 1) // limit)

    paginated = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(paginated)
    profiles = result.scalars().all()

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "links": _build_links(request, page, limit, total_pages),
        "data": profiles,
    }


# ── POST /api/profiles  (admin only) ──────────────────────────────────────────

@router.post(
    "/profiles",
    response_model=ProfileResponse,
    status_code=201,
    response_model_exclude_none=True,
    dependencies=[Depends(require_api_version)],
)
async def create_profile(
    profile_in: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    raw_name = profile_in.name
    if not raw_name or not raw_name.strip():
        raise HTTPException(status_code=400, detail="Missing or empty name")

    name = raw_name.strip().lower()

    stmt = select(Profile).where(Profile.name == name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return {"status": "success", "message": "Profile already exists", "data": existing}

    data = await fetch_classification_data(name)

    new_profile = Profile(
        id=utils.generate_uuidv7(),
        name=name,
        created_at=datetime.now(timezone.utc),
        **data,
    )
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return {"status": "success", "data": new_profile}


# ── GET /api/profiles/export ───────────────────────────────────────────────────

@router.get(
    "/profiles/export",
    dependencies=[Depends(require_api_version)],
)
async def export_profiles(
    request: Request,
    format: str = Query("csv", pattern="^csv$"),
    gender: Optional[str] = None,
    country_id: Optional[str] = None,
    age_group: Optional[str] = None,
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    min_gender_probability: Optional[float] = None,
    min_country_probability: Optional[float] = None,
    sort_by: str = Query("created_at", pattern="^(age|created_at|gender_probability)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_analyst),
):
    """Export all matching profiles as a CSV file."""
    query = await _build_filtered_query(
        db, gender, country_id, age_group, min_age, max_age,
        min_gender_probability, min_country_probability, sort_by, order,
    )
    result = await db.execute(query)
    profiles = result.scalars().all()

    # Stream CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "gender", "gender_probability",
        "age", "age_group", "country_id", "country_name",
        "country_probability", "created_at",
    ])
    for p in profiles:
        writer.writerow([
            p.id, p.name, p.gender, p.gender_probability,
            p.age, p.age_group, p.country_id, p.country_name,
            p.country_probability,
            p.created_at.strftime('%Y-%m-%dT%H:%M:%SZ') if p.created_at else "",
        ])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"profiles_{timestamp}.csv"
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── GET /api/profiles/search ──────────────────────────────────────────────────

@router.get(
    "/profiles/search",
    response_model=ProfileListResponse,
    dependencies=[Depends(require_api_version)],
)
async def search_profiles(
    request: Request,
    q: str = Query(..., min_length=1, description="Natural language search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_analyst),
):
    filters = parse_query(q)
    if filters is None:
        raise HTTPException(status_code=400, detail="Unable to interpret query")

    return await get_profiles_with_filters(
        db, request, page=page, limit=limit, **filters
    )


# ── GET /api/profiles/{id} ────────────────────────────────────────────────────

@router.get(
    "/profiles/{id}",
    response_model=ProfileResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(require_api_version)],
)
async def get_profile(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_analyst),
):
    stmt = select(Profile).where(Profile.id == id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {"status": "success", "data": profile}


# ── GET /api/profiles ─────────────────────────────────────────────────────────

@router.get(
    "/profiles",
    response_model=ProfileListResponse,
    dependencies=[Depends(require_api_version)],
)
async def get_profiles(
    request: Request,
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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_analyst),
):
    return await get_profiles_with_filters(
        db, request,
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
        limit=limit,
    )


# ── DELETE /api/profiles/{id}  (admin only) ───────────────────────────────────

@router.delete(
    "/profiles/{id}",
    status_code=204,
    dependencies=[Depends(require_api_version)],
)
async def delete_profile(
    id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(Profile).where(Profile.id == id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await db.delete(profile)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
