"""
Cases API Endpoints

Endpoints for case management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.case import (
    CaseCreate,
    CaseListResponse,
    CaseResponse,
    CaseUpdate,
)
from db.database import get_db
from db.models import Case

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=CaseListResponse)
async def list_cases(
    status: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> CaseListResponse:
    """List cases with filtering."""
    query = db.query(Case)

    if status:
        query = query.filter(Case.status == status)
    if case_type:
        query = query.filter(Case.case_type == case_type)

    total = query.count()
    cases = query.order_by(Case.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return CaseListResponse(
        total=total,
        cases=[
            CaseResponse(
                case_id=case.case_id,
                title=case.title,
                description=case.description,
                case_type=case.case_type,
                status=case.status,
                priority=case.priority,
                assigned_to=case.assigned_to,
                source_type=case.source_type,
                source_id=case.source_id,
                metadata=case.metadata or {},
                alert_count=len(case.alerts),
                created_at=case.created_at,
                updated_at=case.updated_at,
                resolved_at=case.resolved_at,
                closed_at=case.closed_at,
                resolution_notes=case.resolution_notes,
            )
            for case in cases
        ],
        page=page,
        page_size=page_size,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Get a specific case."""
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    return CaseResponse(
        case_id=case.case_id,
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        status=case.status,
        priority=case.priority,
        assigned_to=case.assigned_to,
        source_type=case.source_type,
        source_id=case.source_id,
        metadata=case.metadata or {},
        alert_count=len(case.alerts),
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        closed_at=case.closed_at,
        resolution_notes=case.resolution_notes,
    )


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Create a new case."""
    db_case = Case(
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        priority=case.priority,
        assigned_to=case.assigned_to,
        source_type=case.source_type,
        source_id=case.source_id,
        metadata=case.metadata or {},
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)

    return CaseResponse(
        case_id=db_case.case_id,
        title=db_case.title,
        description=db_case.description,
        case_type=db_case.case_type,
        status=db_case.status,
        priority=db_case.priority,
        assigned_to=db_case.assigned_to,
        source_type=db_case.source_type,
        source_id=db_case.source_id,
        metadata=db_case.metadata or {},
        alert_count=0,
        created_at=db_case.created_at,
        updated_at=db_case.updated_at,
        resolved_at=None,
        closed_at=None,
        resolution_notes=None,
    )


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Update a case."""
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    update_data = case_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)

    db.commit()
    db.refresh(case)

    return CaseResponse(
        case_id=case.case_id,
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        status=case.status,
        priority=case.priority,
        assigned_to=case.assigned_to,
        source_type=case.source_type,
        source_id=case.source_id,
        metadata=case.metadata or {},
        alert_count=len(case.alerts),
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        closed_at=case.closed_at,
        resolution_notes=case.resolution_notes,
    )


@router.post("/{case_id}/close", response_model=CaseResponse)
async def close_case(
    case_id: str,
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Close a case."""
    case = db.query(Case).filter(Case.case_id == case_id).first()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    from datetime import datetime
    case.status = "closed"
    case.closed_at = datetime.utcnow()

    db.commit()
    db.refresh(case)

    return CaseResponse(
        case_id=case.case_id,
        title=case.title,
        description=case.description,
        case_type=case.case_type,
        status=case.status,
        priority=case.priority,
        assigned_to=case.assigned_to,
        source_type=case.source_type,
        source_id=case.source_id,
        metadata=case.metadata or {},
        alert_count=len(case.alerts),
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        closed_at=case.closed_at,
        resolution_notes=case.resolution_notes,
    )
